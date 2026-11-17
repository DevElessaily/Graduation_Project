package com.example.financial_coach

import android.os.Handler
import android.os.Looper
import io.flutter.plugin.common.EventChannel

object SmsEvents {
    private val main = Handler(Looper.getMainLooper())
    @Volatile private var sink: EventChannel.EventSink? = null

    fun attach(newSink: EventChannel.EventSink?) { sink = newSink }

    fun emit(event: Map<String, Any?>) {
        val current = sink ?: return
        main.post { current.success(event) }
    }
}
EOF