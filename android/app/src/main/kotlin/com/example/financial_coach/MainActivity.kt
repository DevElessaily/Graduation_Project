package com.example.financial_coach

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.provider.Settings
import android.provider.Telephony
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val channelName = "com.example.financial_coach/sms"
    private val eventChannelName = "com.example.financial_coach/sms_events"
    private val permissionRequestCode = 4201
    private val voicePermissionRequestCode = 4202
    private var pendingPermissionResult: MethodChannel.Result? = null
    private var pendingVoiceResult: MethodChannel.Result? = null
    private var speechRecognizer: SpeechRecognizer? = null

    private val voiceChannelName = "com.example.financial_coach/voice"
    private val voiceEventChannelName = "com.example.financial_coach/voice_events"
    private val voicePermissionRequestCode = 4202
    private var pendingVoiceResult: MethodChannel.Result? = null
    private var speechRecognizer: SpeechRecognizer? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "hasPermission" -> result.success(hasReadPermission())
                    "permissionStatus" -> result.success(mapOf(
                        "read" to hasReadPermission(),
                        "receive" to hasReceivePermission(),
                    ))
                    "requestPermission" -> requestSmsPermissions(result)
                    "openSettings" -> { openAppSettings(); result.success(true) }
                    "getInbox" -> {
                        if (!hasReadPermission()) {
                            result.error("permission_denied", "SMS permission has not been granted", null)
                            return@setMethodCallHandler
                        }
                        val limit = call.argument<Int>("limit") ?: 200
                        readInbox(limit, result)
                    }
                    "pendingCount" -> result.success(SmsSync.pendingCount(applicationContext))
                    "flushPending" -> flushPending(result)
                    else -> result.notImplemented()
                }
            }

        EventChannel(flutterEngine.dartExecutor.binaryMessenger, eventChannelName)
            .setStreamHandler(object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                    SmsEvents.attach(events)
                }
                override fun onCancel(arguments: Any?) {
                    SmsEvents.attach(null)
                }
            })
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, voiceChannelName)
    .setMethodCallHandler { call, result ->
        when (call.method) {
            "startVoiceRecording" -> startVoiceRecording(result)
            "stopVoiceRecording" -> {
                val recognizer = speechRecognizer
                if (recognizer == null) {
                    result.error("not_recording", "Voice input is not active", null)
                } else {
                    VoiceEvents.emit(mapOf("type" to "processing"))
                    try { recognizer.stopListening(); result.success(true) }
                    catch (e: Exception) { result.error("stop_failed", e.message ?: "Could not stop", null) }
                }
            }
            "cancelVoiceRecording" -> { cancelVoiceRecording(); result.success(true) }
            else -> result.notImplemented()
        }
    }

EventChannel(flutterEngine.dartExecutor.binaryMessenger, voiceEventChannelName)
    .setStreamHandler(object : EventChannel.StreamHandler {
        override fun onListen(arguments: Any?, events: EventChannel.EventSink?) { VoiceEvents.attach(events) }
        override fun onCancel(arguments: Any?) { VoiceEvents.attach(null) }
    })
        Thread {
            val sync = SmsSync.flush(applicationContext)
            SmsEvents.emit(mapOf(
                "type" to "queue_flushed",
                "pending" to SmsSync.pendingCount(applicationContext),
                "transactions_created" to sync.transactionsCreated,
            ))
        }.start()
    }

    private fun hasReadPermission(): Boolean =
        ContextCompat.checkSelfPermission(this, Manifest.permission.READ_SMS) == PackageManager.PERMISSION_GRANTED

    private fun hasReceivePermission(): Boolean =
        ContextCompat.checkSelfPermission(this, Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED

    private fun requestSmsPermissions(result: MethodChannel.Result) {
        if (hasReadPermission() && hasReceivePermission()) {
            result.success(true); return
        }
        if (pendingPermissionResult != null) {
            result.error("in_progress", "A permission request is already running", null); return
        }
        pendingPermissionResult = result
        ActivityCompat.requestPermissions(this, arrayOf(
            Manifest.permission.READ_SMS, Manifest.permission.RECEIVE_SMS
        ), permissionRequestCode)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
    super.onRequestPermissionsResult(requestCode, permissions, grantResults)
    if (requestCode == 4201) {  // SMS
        pendingPermissionResult?.success(hasReadPermission())
        pendingPermissionResult = null
        if (hasReceivePermission()) Thread { SmsSync.flush(applicationContext) }.start()
    } else if (requestCode == 4202) {  // Voice
        val pending = pendingVoiceResult ?: return
        val granted = grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED
        if (granted) beginSpeechRecognition()
        else { pendingVoiceResult = null; pending.error("microphone_permission_denied", "Allow microphone access", null) }
    }
}

    private fun openAppSettings() {
        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName"))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        startActivity(intent)
    }

    private fun flushPending(result: MethodChannel.Result) {
        Thread {
            val sync = SmsSync.flush(applicationContext)
            val pending = SmsSync.pendingCount(applicationContext)
            runOnUiThread {
                result.success(mapOf(
                    "stored" to sync.stored, "skipped" to sync.skipped,
                    "failed" to sync.failed, "transactions_created" to sync.transactionsCreated,
                    "pending" to pending, "error" to sync.error,
                ))
            }
        }.start()
    }

    private fun readInbox(limit: Int, result: MethodChannel.Result) {
        Thread {
            try {
                val messages = mutableListOf<Map<String, Any?>>()
                val projection = arrayOf(Telephony.Sms._ID, Telephony.Sms.ADDRESS, Telephony.Sms.BODY, Telephony.Sms.DATE)
                contentResolver.query(Telephony.Sms.Inbox.CONTENT_URI, projection, null, null, "${Telephony.Sms.DATE} DESC")?.use { cursor ->
                    val idIndex = cursor.getColumnIndexOrThrow(Telephony.Sms._ID)
                    val addressIndex = cursor.getColumnIndexOrThrow(Telephony.Sms.ADDRESS)
                    val bodyIndex = cursor.getColumnIndexOrThrow(Telephony.Sms.BODY)
                    val dateIndex = cursor.getColumnIndexOrThrow(Telephony.Sms.DATE)
                    var count = 0
                    while (cursor.moveToNext() && count < limit) {
                        messages.add(mapOf(
                            "id" to cursor.getLong(idIndex),
                            "sender" to (cursor.getString(addressIndex) ?: "Unknown"),
                            "message" to (cursor.getString(bodyIndex) ?: ""),
                            "date" to cursor.getLong(dateIndex)
                        ))
                        count++
                    }
                }
                runOnUiThread { result.success(messages) }
            } catch (error: Exception) {
                runOnUiThread { result.error("sms_read_failed", error.message ?: "Could not read the SMS inbox", null) }
            }
        }.start()
    }
    private fun hasMicrophonePermission(): Boolean =
    ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

private fun startVoiceRecording(result: MethodChannel.Result) {
    if (pendingVoiceResult != null) {
        result.error("in_progress", "Voice recognition is already running", null); return
    }
    if (!SpeechRecognizer.isRecognitionAvailable(this)) {
        result.error("voice_unavailable", "No speech recognition service available", null); return
    }
    pendingVoiceResult = result
    if (!hasMicrophonePermission()) {
        ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), voicePermissionRequestCode)
        return
    }
    beginSpeechRecognition()
}

private fun beginSpeechRecognition() {
    if (pendingVoiceResult == null) return
    try {
        val recognizer = SpeechRecognizer.createSpeechRecognizer(this)
        speechRecognizer = recognizer
        recognizer.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) { VoiceEvents.emit(mapOf("type" to "ready")) }
            override fun onBeginningOfSpeech() { VoiceEvents.emit(mapOf("type" to "listening")) }
            override fun onRmsChanged(rmsdB: Float) { VoiceEvents.emit(mapOf("type" to "level", "level" to rmsdB)) }
            override fun onBufferReceived(buffer: ByteArray?) = Unit
            override fun onEndOfSpeech() { VoiceEvents.emit(mapOf("type" to "processing")) }
            override fun onError(error: Int) {
                val message = when (error) {
                    SpeechRecognizer.ERROR_NO_MATCH, SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech recognized. Try again."
                    SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Microphone permission required."
                    else -> "Speech recognition failed (code $error)."
                }
                finishVoiceError(message)
            }
            override fun onResults(results: Bundle?) {
                val transcript = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
                finishVoiceSuccess(transcript)
            }
            override fun onPartialResults(partialResults: Bundle?) {
                val transcript = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
                if (!transcript.isNullOrBlank()) VoiceEvents.emit(mapOf("type" to "partial", "transcript" to transcript))
            }
            override fun onEvent(eventType: Int, params: Bundle?) = Unit
        })
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, java.util.Locale.getDefault().toLanguageTag())
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        VoiceEvents.emit(mapOf("type" to "ready"))
        recognizer.startListening(intent)
    } catch (error: Exception) {
        finishVoiceError(error.message ?: "Could not start speech recognition")
    }
}

private fun finishVoiceSuccess(transcript: String) {
    val result = pendingVoiceResult ?: return
    pendingVoiceResult = null
    destroySpeechRecognizer()
    VoiceEvents.emit(mapOf("type" to "completed", "transcript" to transcript))
    result.success(transcript)
}

private fun finishVoiceError(message: String) {
    val result = pendingVoiceResult ?: return
    pendingVoiceResult = null
    destroySpeechRecognizer()
    VoiceEvents.emit(mapOf("type" to "error", "message" to message))
    result.error("speech_recognition_failed", message, null)
}

private fun cancelVoiceRecording() {
    val result = pendingVoiceResult
    pendingVoiceResult = null
    destroySpeechRecognizer()
    VoiceEvents.emit(mapOf("type" to "cancelled"))
    result?.success(null)
}

private fun destroySpeechRecognizer() {
    val recognizer = speechRecognizer ?: return
    speechRecognizer = null
    try { recognizer.cancel() } catch (_: Exception) {}
    recognizer.destroy()
}

override fun onDestroy() {
    cancelVoiceRecording()
    super.onDestroy()
}

// Add to onRequestPermissionsResult (inside the existing method):
// else if (requestCode == voicePermissionRequestCode) {
//     val pending = pendingVoiceResult ?: return
//     val granted = grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED
//     if (granted) beginSpeechRecognition()
//     else { pendingVoiceResult = null; pending.error("microphone_permission_denied", "Allow microphone access", null) }
// }
}