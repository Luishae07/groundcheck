package com.groundcheck.app

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant
import java.time.ZoneOffset

data class Reading(
    val id: String,
    val time: String,
    val tsunix: Long,
    val temp: Double,
    val alt: Double,
    val pressure: Double?,
    val humidity: Double?,
    val lat: Double,
    val lon: Double
)

data class HourBucket(val hour: Int, val avgTemp: Double, val avgHumidity: Double?, val avgPressure: Double?)

enum class SkyCondition { CLEAR, PARTLY_CLOUDY, CLOUDY, SHOWERS, RAIN, STORM }

fun conditionFor(temp: Double, humidity: Double?, pressure: Double?): SkyCondition {
    if (humidity != null && humidity > 90 && pressure != null && pressure < 985) return SkyCondition.STORM
    if (humidity != null && humidity > 92) return SkyCondition.RAIN
    if (humidity != null && humidity > 85) return SkyCondition.SHOWERS
    if (temp >= 11) return SkyCondition.CLEAR
    if (temp >= 4) return SkyCondition.PARTLY_CLOUDY
    return SkyCondition.CLOUDY
}

fun haversineKm(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
    val r = 6371.0
    val dLat = Math.toRadians(lat2 - lat1)
    val dLon = Math.toRadians(lon2 - lon1)
    val a = Math.sin(dLat / 2).let { it * it } +
        Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2)) *
        Math.sin(dLon / 2).let { it * it }
    return 2 * r * Math.asin(Math.sqrt(a))
}

object WeatherApi {
    private const val BASE = "https://senate-armed-detector-farmers.trycloudflare.com"
    private const val PREDICTOR_BASE = "https://michael-oclc-remind-animals.trycloudflare.com"

    private fun get(url: String): String {
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.connectTimeout = 15_000
        conn.readTimeout = 15_000
        conn.requestMethod = "GET"
        return try {
            conn.inputStream.bufferedReader().use { it.readText() }
        } finally {
            conn.disconnect()
        }
    }

    fun fetchReadings(): List<Reading> {
        val body = get("$BASE/api/data")
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

    fun fetchHourly(): List<HourBucket> {
        val body = get("$PREDICTOR_BASE/predict")
        val o = JSONObject(body)
        val arr = o.getJSONArray("hourly_avg")
        val out = ArrayList<HourBucket>(arr.length())
        for (i in 0 until arr.length()) {
            val b = arr.getJSONObject(i)
            out.add(
                HourBucket(
                    hour = b.getInt("hour"),
                    avgTemp = b.getDouble("avg_temp"),
                    avgHumidity = if (b.isNull("avg_humidity")) null else b.getDouble("avg_humidity"),
                    avgPressure = if (b.isNull("avg_pressure")) null else b.getDouble("avg_pressure")
                )
            )
        }
        return out
    }

    fun hourOfDayUtc(isoTime: String): Int =
        Instant.parse(isoTime).atZone(ZoneOffset.UTC).hour
}
