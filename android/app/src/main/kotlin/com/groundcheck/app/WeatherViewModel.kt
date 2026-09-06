package com.groundcheck.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.WebSocket

data class PredictedHour(val hour: Int, val temp: Double, val humidity: Double?, val pressure: Double?)

data class LiveInfo(val id: String, val temp: Double?, val alt: Double?, val speed: Double?, val rate: Double?, val place: String?)

data class UiState(
    val loading: Boolean = true,
    val error: String? = null,
    val readings: List<Reading> = emptyList(),
    val selected: Reading? = null,
    val distanceKm: Double? = null,
    val locating: Boolean = false,
    val predicted: List<PredictedHour> = emptyList(),
    val live: LiveInfo? = null
)

class WeatherViewModel : ViewModel() {
    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    private var predictorCache: PredictResponse? = null
    private var liveSocket: WebSocket? = null

    fun loadData() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = _state.value.readings.isEmpty(), error = null)
            try {
                val readings = withContext(Dispatchers.IO) { ApiClient.fetchReadings() }
                    .sortedByDescending { it.tsunix }
                val current = _state.value.selected?.let { prev -> readings.find { it.id == prev.id } }
                    ?: readings.firstOrNull()
                _state.value = _state.value.copy(
                    loading = false,
                    readings = readings,
                    selected = current
                )
                current?.let { buildPrediction(it) }
                ensureLiveFeed()
            } catch (e: Exception) {
                _state.value = _state.value.copy(loading = false, error = e.message ?: "failed to load")
            }
        }
    }

    fun selectReading(r: Reading) {
        _state.value = _state.value.copy(selected = r, distanceKm = null)
        buildPrediction(r)
    }

    fun locateNearest(lat: Double, lon: Double) {
        val readings = _state.value.readings
        if (readings.isEmpty()) return
        _state.value = _state.value.copy(locating = true)

        // Prefer readings from the last 24h; fall back to all data if none nearby recently.
        val cutoff = System.currentTimeMillis() / 1000 - 24 * 3600
        val fresh = readings.filter { it.tsunix >= cutoff }
        val pool = if (fresh.isNotEmpty()) fresh else readings

        var best: Reading? = null
        var bestDist = Double.MAX_VALUE
        for (r in pool) {
            val d = haversineKm(lat, lon, r.lat, r.lon)
            if (d < bestDist) { bestDist = d; best = r }
        }
        _state.value = _state.value.copy(selected = best, distanceKm = bestDist, locating = false)
        best?.let { buildPrediction(it) }
    }

    private fun buildPrediction(anchor: Reading) {
        viewModelScope.launch {
            val pred = predictorCache ?: withContext(Dispatchers.IO) {
                try { ApiClient.fetchPrediction() } catch (_: Exception) { null }
            }
            if (pred == null || pred.hourlyAvg.isEmpty()) {
                _state.value = _state.value.copy(predicted = emptyList())
                return@launch
            }
            predictorCache = pred

            fun nearestBucket(h: Int): HourBucket {
                pred.hourlyAvg.find { it.hour == h }?.let { return it }
                return pred.hourlyAvg.minBy { b ->
                    val d = Math.abs(b.hour - h)
                    minOf(d, 24 - d)
                }
            }

            val anchorHour = ApiClient.hourOfDayUtc(anchor.time)
            val anchorBucket = nearestBucket(anchorHour)
            val tempOffset = anchor.temp - anchorBucket.avgTemp
            val humOffset = if (anchorBucket.avgHumidity != null && anchor.humidity != null)
                anchor.humidity - anchorBucket.avgHumidity else 0.0
            val presOffset = if (anchorBucket.avgPressure != null && anchor.pressure != null)
                anchor.pressure - anchorBucket.avgPressure else 0.0

            val chips = (1..5).map { i ->
                val h = (anchorHour + i) % 24
                val b = nearestBucket(h)
                PredictedHour(
                    hour = h,
                    temp = b.avgTemp + tempOffset,
                    humidity = b.avgHumidity?.plus(humOffset),
                    pressure = b.avgPressure?.plus(presOffset)
                )
            }
            _state.value = _state.value.copy(predicted = chips)
        }
    }

    private fun ensureLiveFeed() {
        if (liveSocket != null) return
        liveSocket = ApiClient.connectLiveFeed { id, temp, alt, speed, rate, place ->
            val sel = _state.value.selected
            if (sel != null && sel.id == id) {
                _state.value = _state.value.copy(live = LiveInfo(id, temp, alt, speed, rate, place))
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        liveSocket?.close(1000, null)
    }
}
