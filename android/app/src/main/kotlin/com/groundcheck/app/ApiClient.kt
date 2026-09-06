package com.groundcheck.app

import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.util.concurrent.TimeUnit

object ApiClient {
    private const val BASE = "https://senate-armed-detector-farmers.trycloudflare.com"
    private const val PREDICTOR_BASE = "https://michael-oclc-remind-animals.trycloudflare.com"
    private const val LIVE_WS = "wss://calcium-shareware-sequence-hills.trycloudflare.com"

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    fun fetchReadings(): List<Reading> {
        val req = Request.Builder().url("$BASE/api/data").build()
        client.newCall(req).execute().use { resp ->
            val body = resp.body?.string() ?: return emptyList()
            val arr = JSONArray(body)
            val out = ArrayList<Reading>(arr.length())
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                out.add(
                    Reading(
                        id = o.getString("id"),
                        time = o.getString("time"),
                        tsunix = o.optLong("tsunix", 0),
                        temp = o.getDouble("temp"),
                        alt = o.optDouble("alt", 0.0),
                        pressure = if (o.isNull("pressure")) null else o.getDouble("pressure"),
                        humidity = if (o.isNull("humidity")) null else o.getDouble("humidity"),
                        lat = o.getDouble("lat"),
                        lon = o.getDouble("lon")
                    )
                )
            }
            return out
        }
    }

    fun fetchPrediction(): PredictResponse? {
        val req = Request.Builder().url("$PREDICTOR_BASE/predict").build()
        client.newCall(req).execute().use { resp ->
            val body = resp.body?.string() ?: return null
            val o = JSONObject(body)
            val arr = o.getJSONArray("hourly_avg")
            val buckets = ArrayList<HourBucket>(arr.length())
            for (i in 0 until arr.length()) {
                val b = arr.getJSONObject(i)
                buckets.add(
                    HourBucket(
                        hour = b.getInt("hour"),
                        avgTemp = b.getDouble("avg_temp"),
                        avgHumidity = if (b.isNull("avg_humidity")) null else b.getDouble("avg_humidity"),
                        avgPressure = if (b.isNull("avg_pressure")) null else b.getDouble("avg_pressure"),
                        samples = b.getInt("samples")
                    )
                )
            }
            return PredictResponse(
                generated = o.getString("generated"),
                sampleCount = o.getInt("sample_count"),
                hourlyAvg = buckets
            )
        }
    }

    fun connectLiveFeed(
        onMessage: (id: String, temp: Double?, alt: Double?, speed: Double?, rate: Double?, place: String?) -> Unit
    ): WebSocket {
        val req = Request.Builder().url(LIVE_WS).build()
        return client.newWebSocket(req, object : WebSocketListener() {
            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val data = JSONObject(text)
                    val feats = data.optJSONArray("features") ?: return
                    for (i in 0 until feats.length()) {
                        val f = feats.getJSONObject(i)
                        val p = f.getJSONObject("properties")
                        onMessage(
                            p.getString("id"),
                            if (p.isNull("temp")) null else p.getDouble("temp"),
                            if (p.isNull("alti")) null else p.getDouble("alti"),
                            if (p.isNull("speed")) null else p.getDouble("speed"),
                            if (p.isNull("rate")) null else p.getDouble("rate"),
                            if (p.has("places") && !p.isNull("places")) p.getString("places") else null
                        )
                    }
                } catch (_: Exception) { /* ignore malformed frames */ }
            }
        })
    }

    fun hourOfDayUtc(isoTime: String): Int {
        return Instant.parse(isoTime).atZone(java.time.ZoneOffset.UTC).hour
    }
}
