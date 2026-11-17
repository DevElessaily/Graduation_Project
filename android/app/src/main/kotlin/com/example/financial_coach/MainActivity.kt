package com.example.financial_coach

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
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
    private var pendingPermissionResult: MethodChannel.Result? = null

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
        ), 4201)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 4201) {
            pendingPermissionResult?.success(hasReadPermission())
            pendingPermissionResult = null
            if (hasReceivePermission()) Thread { SmsSync.flush(applicationContext) }.start()
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
}
EOF