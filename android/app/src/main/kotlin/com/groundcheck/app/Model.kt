package com.groundcheck.app

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

data class HourBucket(
    val hour: Int,
    val avgTemp: Double,
    val avgHumidity: Double?,
    val avgPressure: Double?,
    val samples: Int
)

data class PredictResponse(
    val generated: String,
    val sampleCount: Int,
    val hourlyAvg: List<HourBucket>
)

enum class SkyCondition { CLEAR, PARTLY_CLOUDY, CLOUDY, SHOWERS, RAIN, STORM }

fun conditionFor(temp: Double, humidity: Double?, pressure: Double?): SkyCondition {
    if (humidity != null && humidity > 90 && pressure != null && pressure < 985) return SkyCondition.STORM
    if (humidity != null && humidity > 92) return SkyCondition.RAIN
    if (humidity != null && humidity > 85) return SkyCondition.SHOWERS
    if (temp >= 11) return SkyCondition.CLEAR
    if (temp >= 4) return SkyCondition.PARTLY_CLOUDY
    return SkyCondition.CLOUDY
}

fun conditionLabel(c: SkyCondition): String = when (c) {
    SkyCondition.STORM -> "Thunderstorms possible"
    SkyCondition.RAIN -> "Rain likely"
    SkyCondition.SHOWERS -> "Showers possible"
    SkyCondition.CLEAR -> "Clear"
    SkyCondition.PARTLY_CLOUDY -> "Partly cloudy"
    SkyCondition.CLOUDY -> "Cool, cloudy"
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
