package com.example.financial_coach

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import android.util.Log
import org.json.JSONObject

class SmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        val parts = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (parts.isNullOrEmpty()) return

        val bodies = LinkedHashMap<String, StringBuilder>()
        var timestamp = 0L
        for (part in parts) {
            val sender = part.originatingAddress ?: part.displayOriginatingAddress ?: "Unknown"
            bodies.getOrPut(sender) { StringBuilder() }.append(part.messageBody ?: "")
            if (timestamp == 0L) timestamp = part.timestampMillis
        }
        if (timestamp == 0L) timestamp = System.currentTimeMillis()
        val epochSeconds = timestamp / 1000

        val items = bodies.map { (sender, body) ->
            JSONObject().put("sender", sender).put("message", body.toString()).put("date", epochSeconds)
        }

        for (item in items) {
            SmsEvents.emit(mapOf("type" to "received", "sender" to item.optString("sender"),
                "message" to item.optString("message"), "date" to epochSeconds))
        }

        val pending = goAsync()
        Thread {
            try {
                val result = SmsSync.enqueueAndSync(context.applicationContext, items)
                SmsEvents.emit(mapOf("type" to if (result.ok) "synced" else "sync_failed",
                    "stored" to result.stored, "skipped" to result.skipped,
                    "queued" to result.queued, "transactions_created" to result.transactionsCreated,
                    "pending" to SmsSync.pendingCount(context.applicationContext), "error" to result.error))
            } catch (error: Throwable) {
                Log.w("SmsReceiver", "Live SMS sync failed", error)
                SmsEvents.emit(mapOf("type" to "sync_failed", "error" to (error.message ?: error.javaClass.simpleName)))
            } finally { pending.finish() }
        }.start()
    }
}
EOF