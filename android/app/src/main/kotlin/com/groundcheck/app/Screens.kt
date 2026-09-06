package com.groundcheck.app

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocationSearching
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
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

/** Matches desktop's .panel: dark card, rounded, subtle border, padded header. */
@Composable
private fun Panel(title: String, subtitle: String? = null, content: @Composable () -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Panel)
            .padding(16.dp)
    ) {
        Row(verticalAlignment = Alignment.Bottom) {
            Text(title, fontWeight = FontWeight.Bold, fontSize = 15.sp, color = Ink)
            if (subtitle != null) {
                Spacer(Modifier.width(6.dp))
                Text(subtitle, fontSize = 11.sp, color = InkFaint)
            }
        }
        Spacer(Modifier.height(10.dp))
        content()
    }
}

@Composable
fun TodayScreen(
    state: UiState,
    onRefreshLocation: () -> Unit,
    onOpenMap: () -> Unit
) {
    val sel = state.selected
    Column(
        Modifier
            .fillMaxSize()
            .background(Panel2)
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        // --- Hero: matches desktop's .hero diagonal sky gradient ---
        Box(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(20.dp))
                .background(Brush.linearGradient(listOf(SkyTop, SkyMid, SkyBot)))
                .padding(20.dp)
        ) {
            if (sel == null) {
                Text(if (state.loading) "Loading…" else "No data", color = Ink)
            } else {
                val cond = conditionFor(sel.temp, sel.humidity, sel.pressure)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(iconFor(cond), contentDescription = null, tint = Color.White, modifier = Modifier.size(64.dp))
                    Spacer(Modifier.width(16.dp))
                    Column(Modifier.weight(1f)) {
                        Text(
                            (if (state.distanceKm != null) "Nearest station: " else "Newest reading: ") + sel.id,
                            color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = 14.sp
                        )
                        Text(
                            "%.1f°".format(sel.temp),
                            color = Color.White, fontWeight = FontWeight.Black, fontSize = 44.sp
                        )
                        Text(conditionLabel(cond), color = Color.White.copy(alpha = 0.9f), fontSize = 13.sp)
                        if (state.distanceKm != null) {
                            Text("%.0f km from you".format(state.distanceKm), color = Color.White.copy(alpha = 0.75f), fontSize = 11.sp)
                        }
                        Text(fmtTime(sel.time), color = Color.White.copy(alpha = 0.65f), fontSize = 11.sp)
                    }
                }

                if (state.live != null && state.live.id == sel.id) {
                    Spacer(Modifier.height(14.dp))
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(14.dp))
                            .background(Color(0xFFC0453F))
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(Modifier.size(8.dp).clip(CircleShape).background(Color.White))
                        Spacer(Modifier.width(8.dp))
                        Column(Modifier.weight(1f)) {
                            Text("Live now — your station is in flight", color = Color.White, fontSize = 11.sp)
                            Text(
                                "${state.live.alt?.toInt() ?: "—"} m" +
                                    (state.live.speed?.let { " · %.0f km/h".format(it) } ?: ""),
                                color = Color.White, fontSize = 13.sp
                            )
                        }
                        state.live.temp?.let {
                            Text("%.1f°".format(it), color = Color.White, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        }
                    }
                }

                Spacer(Modifier.height(14.dp))
                Row(
                    Modifier
                        .clip(RoundedCornerShape(999.dp))
                        .background(Color.White.copy(alpha = 0.16f))
                        .clickable(enabled = !state.locating, onClick = onRefreshLocation)
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Filled.LocationSearching, contentDescription = null, tint = Color.White, modifier = Modifier.size(14.dp))
                    Spacer(Modifier.width(6.dp))
                    Text(if (state.locating) "Locating…" else "Use my location", color = Color.White, fontSize = 12.sp)
                }
            }
        }

        Spacer(Modifier.height(14.dp))

        if (sel != null) {
            Row(Modifier.fillMaxWidth()) {
                StatCard("Humidity", sel.humidity?.let { "%.0f%%".format(it) } ?: "—", Modifier.weight(1f))
                Spacer(Modifier.width(10.dp))
                StatCard("Pressure", sel.pressure?.let { "%.0f hPa".format(it) } ?: "—", Modifier.weight(1f))
                Spacer(Modifier.width(10.dp))
                StatCard("Altitude", "${sel.alt.toInt()} m", Modifier.weight(1f))
            }
            Spacer(Modifier.height(14.dp))
        }

        if (state.predicted.isNotEmpty()) {
            Panel(title = "Next hours", subtitle = "from 7-day pattern") {
                LazyRow {
                    items(state.predicted) { p ->
                        val cond = conditionFor(p.temp, p.humidity, p.pressure)
                        Column(
                            Modifier
                                .padding(end = 8.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .background(Panel2)
                                .padding(10.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Text("%02d:00".format(p.hour), fontSize = 10.sp, color = InkFaint)
                            Icon(iconFor(cond), contentDescription = null, tint = Ink, modifier = Modifier.size(22.dp).padding(vertical = 4.dp))
                            Text("%.0f°".format(p.temp), fontWeight = FontWeight.Bold, color = Ink, fontSize = 15.sp)
                        }
                    }
                }
            }
            Spacer(Modifier.height(14.dp))
        }

        Panel(title = "Station map", subtitle = "${state.readings.size} stations") {
            Box(
                Modifier
                    .fillMaxWidth()
                    .height(220.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .clickable(onClick = onOpenMap)
            ) {
                MapScreenView(readings = state.readings, onMarkerClick = {})
            }
        }

        if (state.error != null) {
            Spacer(Modifier.height(14.dp))
            Text("Data feed unreachable: ${state.error}", color = Color(0xFFE0824A), fontSize = 12.sp)
        }

        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun StatCard(label: String, value: String, modifier: Modifier = Modifier) {
    Column(
        modifier
            .clip(RoundedCornerShape(14.dp))
            .background(Panel)
            .padding(12.dp)
    ) {
        Text(label.uppercase(), fontSize = 10.sp, color = InkFaint)
        Text(value, fontWeight = FontWeight.Bold, fontSize = 17.sp, color = Ink)
    }
}

@Composable
fun StationsScreen(readings: List<Reading>, onSelect: (Reading) -> Unit) {
    val stations = readings.distinctBy { it.id }
    Column(Modifier.fillMaxSize().background(Panel2).padding(16.dp)) {
        Text("All stations", fontWeight = FontWeight.Bold, color = Ink)
        Text("${stations.size} stations", fontSize = 11.sp, color = InkFaint)
        Spacer(Modifier.height(10.dp))
        LazyVerticalGrid(
            columns = GridCells.Adaptive(minSize = 150.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(stations) { r ->
                val cond = conditionFor(r.temp, r.humidity, r.pressure)
                Column(
                    Modifier
                        .clip(RoundedCornerShape(12.dp))
                        .background(Panel)
                        .clickable { onSelect(r) }
                        .padding(12.dp)
                ) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Icon(iconFor(cond), contentDescription = null, tint = Ink, modifier = Modifier.size(22.dp))
                        Spacer(Modifier.weight(1f))
                        Text(
                            "%.1f°".format(r.temp),
                            color = tempColor(r.temp), fontWeight = FontWeight.Bold, fontSize = 16.sp
                        )
                    }
                    Spacer(Modifier.height(6.dp))
                    Text(r.id, fontFamily = FontFamily.Monospace, fontSize = 11.sp, color = InkDim)
                    Text("${fmtTime(r.time)} · ${r.alt.toInt()} m", fontSize = 10.sp, color = InkFaint)
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
    LazyColumn(
        Modifier
            .fillMaxSize()
            .background(Panel2)
            .padding(16.dp)
    ) {
        item { Text("FAQ", fontWeight = FontWeight.Bold, color = Ink, modifier = Modifier.padding(bottom = 10.dp)) }
        items(items) { (q, a) ->
            Column(
                Modifier
                    .fillMaxWidth()
                    .padding(bottom = 8.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .background(Panel)
                    .padding(12.dp)
            ) {
                Text(q, fontWeight = FontWeight.Bold, color = Ink, fontSize = 13.sp)
                Spacer(Modifier.height(4.dp))
                Text(a, fontSize = 12.sp, color = InkDim)
            }
        }
    }
}
