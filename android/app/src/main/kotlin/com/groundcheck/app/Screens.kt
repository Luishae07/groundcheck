package com.groundcheck.app

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocationSearching
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

private fun fmtTime(iso: String): String = try {
    val t = Instant.parse(iso).atZone(ZoneOffset.UTC)
    t.format(DateTimeFormatter.ofPattern("MMM d, HH:mm 'UTC'"))
} catch (_: Exception) { iso }

@Composable
fun TodayScreen(
    state: UiState,
    onRefreshLocation: () -> Unit
) {
    val sel = state.selected
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        Box(
            Modifier
                .fillMaxWidth()
                .background(Brush.verticalGradient(listOf(Color(0xFF4A7FB5), Color(0xFFA9CBE3))))
                .padding(20.dp)
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                if (sel == null) {
                    Text(if (state.loading) "Loading…" else "No data", color = Color.White)
                } else {
                    val cond = conditionFor(sel.temp, sel.humidity, sel.pressure)
                    Text(
                        (if (state.distanceKm != null) "Nearest station: " else "Newest reading: ") + sel.id,
                        color = Color.White, fontWeight = FontWeight.SemiBold
                    )
                    if (state.distanceKm != null) {
                        Text(
                            "%.0f km from you".format(state.distanceKm),
                            color = Color.White.copy(alpha = 0.85f), fontSize = 12.sp
                        )
                    }
                    Icon(iconFor(cond), contentDescription = null, tint = Color.White, modifier = Modifier.size(72.dp).padding(top = 8.dp))
                    Text(
                        "%.1f°".format(sel.temp),
                        color = Color.White, fontWeight = FontWeight.Bold, fontSize = 56.sp
                    )
                    Text(conditionLabel(cond), color = Color.White.copy(alpha = 0.9f))
                    Text(fmtTime(sel.time), color = Color.White.copy(alpha = 0.7f), fontSize = 12.sp)

                    if (state.live != null && state.live.id == sel.id) {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color(0xFFC0453F)),
                            modifier = Modifier.fillMaxWidth().padding(top = 12.dp)
                        ) {
                            Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                                Box(Modifier.size(8.dp).clip(CircleShape).background(Color.White))
                                Spacer(Modifier.width(8.dp))
                                Column {
                                    Text("Live now — your station is in flight", color = Color.White, fontSize = 11.sp)
                                    Text(
                                        "${state.live.alt?.toInt() ?: "—"} m" +
                                            (state.live.speed?.let { " · %.0f km/h".format(it) } ?: ""),
                                        color = Color.White, fontSize = 13.sp
                                    )
                                }
                                Spacer(Modifier.weight(1f))
                                state.live.temp?.let {
                                    Text("%.1f°".format(it), color = Color.White, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                                }
                            }
                        }
                    }
                }

                Spacer(Modifier.height(12.dp))
                Button(onClick = onRefreshLocation, enabled = !state.locating) {
                    Icon(Icons.Filled.LocationSearching, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(6.dp))
                    Text(if (state.locating) "Locating…" else "Use my location")
                }
            }
        }

        if (sel != null) {
            Row(Modifier.fillMaxWidth().padding(16.dp)) {
                StatTile("Humidity", sel.humidity?.let { "%.0f%%".format(it) } ?: "—", Modifier.weight(1f))
                Spacer(Modifier.width(8.dp))
                StatTile("Pressure", sel.pressure?.let { "%.0f hPa".format(it) } ?: "—", Modifier.weight(1f))
                Spacer(Modifier.width(8.dp))
                StatTile("Altitude", "${sel.alt.toInt()} m", Modifier.weight(1f))
            }
        }

        if (state.predicted.isNotEmpty()) {
            Text("Next hours", fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(horizontal = 16.dp))
            Text("from 7-day pattern", color = Color.Gray, fontSize = 11.sp, modifier = Modifier.padding(horizontal = 16.dp))
            LazyRow(Modifier.padding(vertical = 8.dp)) {
                items(state.predicted) { p ->
                    val cond = conditionFor(p.temp, p.humidity, p.pressure)
                    Card(Modifier.padding(horizontal = 6.dp)) {
                        Column(
                            Modifier.padding(12.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Text("%02d:00".format(p.hour), fontSize = 11.sp, color = Color.Gray)
                            Icon(iconFor(cond), contentDescription = null, modifier = Modifier.size(24.dp).padding(vertical = 4.dp))
                            Text("%.0f°".format(p.temp), fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }

        if (state.error != null) {
            Text(
                "Data feed unreachable: ${state.error}",
                color = Color.Red,
                modifier = Modifier.padding(16.dp)
            )
        }

        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun StatTile(label: String, value: String, modifier: Modifier = Modifier) {
    Card(modifier) {
        Column(Modifier.padding(12.dp)) {
            Text(label.uppercase(), fontSize = 10.sp, color = Color.Gray)
            Text(value, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        }
    }
}

@Composable
fun StationsScreen(readings: List<Reading>, onSelect: (Reading) -> Unit) {
    val byStation = readings.distinctBy { it.id }
    LazyColumn(Modifier.fillMaxSize().padding(12.dp)) {
        item { Text("${byStation.size} stations", color = Color.Gray, modifier = Modifier.padding(bottom = 8.dp)) }
        items(byStation) { r ->
            val cond = conditionFor(r.temp, r.humidity, r.pressure)
            Card(
                Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp),
            ) {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .padding(12.dp)
                        .clip(RoundedCornerShape(8.dp)),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(iconFor(cond), contentDescription = null, modifier = Modifier.size(28.dp))
                    Spacer(Modifier.width(12.dp))
                    Column(Modifier.weight(1f)) {
                        Text(r.id, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace, fontSize = 13.sp)
                        Text("${fmtTime(r.time)} · ${r.alt.toInt()} m alt", fontSize = 11.sp, color = Color.Gray)
                    }
                    Text("%.1f°".format(r.temp), fontWeight = FontWeight.Bold, fontSize = 18.sp)
                }
            }
        }
    }
}

@Composable
fun FaqScreen() {
    val items = listOf(
        "Why use this?" to "You get to see real, live sensor data straight from actual weather balloons in flight right now — the same raw measurements meteorologists use to calibrate forecasts.",
        "Where does this data come from?" to "Live radiosonde telemetry from sonde.mine.nu / zeesen.mine.nu.",
        "Why are some temperatures missing?" to "Radiosondes spend most of a flight at high altitude, where it's routinely far below freezing — those readings are filtered out; only ground-level (≤500m), non-negative readings are shown.",
        "Why does it say a station is far from me?" to "This isn't a dense sensor network — it's wherever balloons happened to fly. If nothing launched near you recently, the nearest valid reading may be hundreds of km away.",
        "What's the 'Next hours' prediction?" to "A real prediction built purely from our own 7-day history: the average temperature/humidity/pressure for each hour-of-day, anchored to the current actual reading. Not an external forecast model.",
        "What's the 'Live now' banner?" to "When the station currently shown is an actual balloon still in flight, we stream its live telemetry over a WebSocket connection to zeesen.mine.nu."
    )
    LazyColumn(Modifier.fillMaxSize().padding(16.dp)) {
        items(items) { (q, a) ->
            Card(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                Column(Modifier.padding(12.dp)) {
                    Text(q, fontWeight = FontWeight.Bold, modifier = Modifier.padding(bottom = 4.dp))
                    Text(a, fontSize = 13.sp, color = Color.DarkGray)
                }
            }
        }
    }
}
