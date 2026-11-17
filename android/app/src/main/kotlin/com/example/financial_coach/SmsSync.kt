package com.example.financial_coach

import android.content.Context
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL

data class SmsSyncResult(
    val stored: Int = 0, val skipped: Int = 0, val queued: Int = 0,
    val failed: Int = 0, val transactionsCreated: Int = 0, val error: String? = null
) { val ok: Boolean get() = error == null }

object SmsSync {
    private const val TAG = "SmsSync"
    private const val QUEUE_PREFS = "sms_sync_queue"
    private const val QUEUE_KEY = "pending"
    private const val CHUNK = 100
    private const val DEFAULT_BASE_URL = "http://10.0.2.2:8000"

    fun baseUrl(context: Context): String {
        val prefs = context.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
        val stored = prefs.getString("flutter.backend_base_url", null) ?: prefs.getString("backend_base_url", null)
        val raw = stored?.takeIf { it.isNotBlank() } ?: DEFAULT_BASE_URL
        return normalizeBaseUrl(raw.trim().trimEnd('/'))
    }

    private fun normalizeBaseUrl(raw: String): String {
        return try {
            val uri = URI(raw)
            val host = uri.host?.trim('[', ']')?.lowercase() ?: return raw
            if (!uri.scheme.equals("https", ignoreCase = true) || !isLocalHost(host)) return raw
            URI("http", uri.userInfo, host, uri.port, uri.path, uri.query, uri.fragment).toString().trimEnd('/')
        } catch (_: Exception) { raw }
    }

    private fun isLocalHost(host: String): Boolean {
        if (host == "localhost" || host == "10.0.2.2" || host.endsWith(".local")) return true
        val octets = host.split('.').mapNotNull { it.toIntOrNull() }
        if (octets.size != 4 || octets.any { it !in 0..255 }) return false
        return octets[0] == 10 || (octets[0] == 192 && octets[1] == 168) ||
            (octets[0] == 172 && octets[1] in 16..31) || octets[0] == 127
    }

    private fun queuePrefs(context: Context) = context.getSharedPreferences(QUEUE_PREFS, Context.MODE_PRIVATE)

    fun pendingCount(context: Context): Int = readQueue(context).length()

    private fun readQueue(context: Context): JSONArray {
        val raw = queuePrefs(context).getString(QUEUE_KEY, null) ?: return JSONArray()
        return try { JSONArray(raw) } catch (e: Exception) { JSONArray() }
    }

    private fun writeQueue(context: Context, queue: JSONArray) {
        val editor = queuePrefs(context).edit()
        if (queue.length() == 0) editor.remove(QUEUE_KEY) else editor.putString(QUEUE_KEY, queue.toString())
        editor.apply()
    }

    private fun keyOf(item: JSONObject): String =
        "${item.optString("sender")}|${item.optString("message")}|${item.optLong("date", 0L)}"

    @Synchronized
    fun enqueue(context: Context, items: List<JSONObject>): Int {
        if (items.isEmpty()) return 0
        val queue = readQueue(context)
        val known = HashSet<String>()
        for (i in 0 until queue.length()) { val item = queue.optJSONObject(i) ?: continue; known.add(keyOf(item)) }
        var added = 0
        for (item in items) {
            if (known.add(keyOf(item))) { queue.put(item); added++ }
        }
        if (added > 0) writeQueue(context, queue)
        return added
    }

    @Synchronized
    fun enqueueAndSync(context: Context, items: List<JSONObject>): SmsSyncResult {
        val added = enqueue(context, items)
        return flush(context).copy(queued = added)
    }

    @Synchronized
    fun flush(context: Context): SmsSyncResult {
        var queue = readQueue(context)
        if (queue.length() == 0) return SmsSyncResult()
        var stored = 0; var skipped = 0; var transactionsCreated = 0
        while (queue.length() > 0) {
            val take = minOf(queue.length(), CHUNK)
            val batch = JSONArray()
            for (i in 0 until take) batch.put(queue.get(i))
            val response = post(context, batch)
            if (!response.ok) {
                return SmsSyncResult(stored = stored, skipped = skipped, failed = batch.length(),
                    transactionsCreated = transactionsCreated, error = response.error)
            }
            stored += response.stored; skipped += response.skipped
            transactionsCreated += response.transactionsCreated
            val rest = JSONArray()
            for (i in take until queue.length()) rest.put(queue.get(i))
            queue = rest; writeQueue(context, queue)
        }
        return SmsSyncResult(stored = stored, skipped = skipped, transactionsCreated = transactionsCreated)
    }

    private fun post(context: Context, items: JSONArray): SmsSyncResult {
        var connection: HttpURLConnection? = null
        try {
            val url = URL("${baseUrl(context)}/api/sms/bulk")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"; connectTimeout = 10_000; readTimeout = 20_000
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                setRequestProperty("Accept", "application/json")
            }
            connection = conn
            val payload = JSONObject().put("items", items).toString()
            OutputStreamWriter(conn.outputStream, Charsets.UTF_8).use { it.write(payload) }
            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val text = stream?.let { BufferedReader(InputStreamReader(it, Charsets.UTF_8)).use { r -> r.readText() } }.orEmpty()
            if (code !in 200..299) return SmsSyncResult(error = "HTTP $code ${text.take(160)}".trim())
            val body = try { JSONObject(text) } catch (_: Exception) { JSONObject() }
            return SmsSyncResult(stored = body.optInt("stored", 0),
                skipped = body.optInt("skipped", 0),
                transactionsCreated = body.optInt("transactions_created", 0))
        } catch (error: Throwable) {
            Log.w(TAG, "Could not reach the backend", error)
            return SmsSyncResult(error = error.message ?: error.javaClass.simpleName)
        } finally { connection?.disconnect() }
    }
}
EOF