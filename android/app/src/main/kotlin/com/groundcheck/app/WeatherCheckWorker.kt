package com.groundcheck.app

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class WeatherCheckWorker(appContext: Context, params: WorkerParameters) :
    CoroutineWorker(appContext, params) {

    companion object {
        const val CHANNEL_ID = "groundcheck_alerts"
        const val NOTIF_ID = 1001
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            val hasLocation = ContextCompat.checkSelfPermission(
                applicationContext, Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
            if (!hasLocation) return@withContext Result.success() // nothing we can check without a location

            val lm = applicationContext.getSystemService(Context.LOCATION_SERVICE) as LocationManager
            var lat: Double? = null
            var lon: Double? = null
            for (provider in listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)) {
                try {
                    lm.getLastKnownLocation(provider)?.let {
                        lat = it.latitude; lon = it.longitude
                    }
                } catch (_: SecurityException) { }
                if (lat != null) break
            }
            if (lat == null || lon == null) return@withContext Result.success()

            val readings = WeatherApi.fetchReadings()
            if (readings.isEmpty()) return@withContext Result.success()

            val cutoff = System.currentTimeMillis() / 1000 - 24 * 3600
            val fresh = readings.filter { it.tsunix >= cutoff }
            val pool = fresh.ifEmpty { readings }
            val nearest = pool.minByOrNull { haversineKm(lat!!, lon!!, it.lat, it.lon) } ?: return@withContext Result.success()

            val currentCond = conditionFor(nearest.temp, nearest.humidity, nearest.pressure)
            var alertCond: SkyCondition? = if (currentCond == SkyCondition.STORM || currentCond == SkyCondition.RAIN) currentCond else null
            var whenLabel = "now"

            if (alertCond == null) {
                // Also check the next few predicted hours (same anchoring logic as the app's predictor).
                val hourly = try { WeatherApi.fetchHourly() } catch (_: Exception) { emptyList() }
                if (hourly.isNotEmpty()) {
                    fun nearestBucket(h: Int) = hourly.find { it.hour == h }
                        ?: hourly.minBy { b -> minOf(Math.abs(b.hour - h), 24 - Math.abs(b.hour - h)) }

                    val anchorHour = WeatherApi.hourOfDayUtc(nearest.time)
                    val anchorBucket = nearestBucket(anchorHour)
                    val tempOffset = nearest.temp - anchorBucket.avgTemp
                    val humOffset = if (anchorBucket.avgHumidity != null && nearest.humidity != null)
                        nearest.humidity - anchorBucket.avgHumidity else 0.0
                    val presOffset = if (anchorBucket.avgPressure != null && nearest.pressure != null)
                        nearest.pressure - anchorBucket.avgPressure else 0.0

                    for (i in 1..5) {
                        val h = (anchorHour + i) % 24
                        val b = nearestBucket(h)
                        val pTemp = b.avgTemp + tempOffset
                        val pHum = b.avgHumidity?.plus(humOffset)
                        val pPres = b.avgPressure?.plus(presOffset)
                        val c = conditionFor(pTemp, pHum, pPres)
                        if (c == SkyCondition.STORM || c == SkyCondition.RAIN) {
                            alertCond = c
                            whenLabel = "around %02d:00 UTC".format(h)
                            break
                        }
                    }
                }
            }

            if (alertCond != null) {
                notify(alertCond!!, whenLabel, nearest.id)
            }
            Result.success()
        } catch (_: Exception) {
            Result.success() // never crash a background worker over a network hiccup
        }
    }

    private fun notify(cond: SkyCondition, whenLabel: String, stationId: String) {
        val nm = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID, "Weather alerts", NotificationManager.IMPORTANCE_DEFAULT
            ).apply { description = "Rain/thunderstorm alerts from nearby radiosonde readings" }
            nm.createNotificationChannel(channel)
        }

        val title = if (cond == SkyCondition.STORM) "Thunderstorm possible near you" else "Rain likely near you"
        val text = "Based on station $stationId, $whenLabel."

        if (ContextCompat.checkSelfPermission(
                applicationContext, Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
        ) return

        val notification = NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(title)
            .setContentText(text)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .build()

        nm.notify(NOTIF_ID, notification)
    }
}
