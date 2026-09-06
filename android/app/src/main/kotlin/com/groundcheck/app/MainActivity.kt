package com.groundcheck.app

import android.Manifest
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Place
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.osmdroid.config.Configuration

class MainActivity : ComponentActivity() {

    private val viewModel: WeatherViewModel by viewModels()

    private val locationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) requestLocationOnce()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Must run before any MapView is created, or osmdroid throws/crashes
        // trying to resolve its tile cache directory. Pointing it at our own
        // cache dir directly avoids needing a SharedPreferences round-trip.
        val osmConf = Configuration.getInstance()
        osmConf.userAgentValue = packageName
        osmConf.osmdroidBasePath = java.io.File(cacheDir, "osmdroid").apply { mkdirs() }
        osmConf.osmdroidTileCache = java.io.File(osmConf.osmdroidBasePath, "tiles").apply { mkdirs() }

        viewModel.loadData()

        setContent {
            MaterialTheme(colorScheme = GroundcheckColorScheme) {
                Surface(color = Panel2) {
                    AppRoot(
                        viewModel = viewModel,
                        onRequestLocation = { ensureLocationPermissionThenLocate() }
                    )
                }
            }
        }
    }

    private fun ensureLocationPermissionThenLocate() {
        val granted = ContextCompat.checkSelfPermission(
            this, Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        if (granted) requestLocationOnce()
        else locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
    }

    private fun requestLocationOnce() {
        val lm = getSystemService(LOCATION_SERVICE) as LocationManager
        val providers = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
        for (provider in providers) {
            try {
                val last = lm.getLastKnownLocation(provider)
                if (last != null) {
                    viewModel.locateNearest(last.latitude, last.longitude)
                    return
                }
            } catch (_: SecurityException) { }
        }
        try {
            lm.requestSingleUpdate(LocationManager.GPS_PROVIDER, { loc ->
                viewModel.locateNearest(loc.latitude, loc.longitude)
            }, mainLooper)
        } catch (_: Exception) { }
    }
}

private data class NavDest(val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector)

private val destinations = listOf(
    NavDest("Today", Icons.Filled.WbSunny),
    NavDest("Map", Icons.Filled.Map),
    NavDest("Stations", Icons.Filled.Place),
    NavDest("FAQ", Icons.Filled.HelpOutline),
)

@Composable
fun AppRoot(viewModel: WeatherViewModel, onRequestLocation: () -> Unit) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var tab by remember { mutableIntStateOf(0) }

    fun selectAndShowToday(r: Reading) {
        viewModel.selectReading(r)
        tab = 0
    }

    Column(Modifier.fillMaxSize()) {
        // --- Top bar: brand + live dot, matching desktop's .topbar ---
        Row(
            Modifier
                .fillMaxWidth()
                .background(Panel)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Groundcheck", fontWeight = FontWeight.Black, fontSize = 17.sp, color = Ink)
            Spacer(Modifier.weight(1f))
            Box(Modifier.size(7.dp).clip(CircleShape).background(Color(0xFF3EA86B)))
            Spacer(Modifier.width(6.dp))
            Text("live feed", fontSize = 12.sp, color = InkDim)
        }

        Row(Modifier.fillMaxSize()) {
            // --- Left icon sidebar, matching desktop's .sidebar ---
            Column(
                Modifier
                    .fillMaxHeight()
                    .width(72.dp)
                    .background(Panel)
                    .padding(vertical = 12.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                destinations.forEachIndexed { i, d ->
                    val selected = tab == i
                    Column(
                        Modifier
                            .padding(vertical = 4.dp, horizontal = 8.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .background(if (selected) Accent.copy(alpha = 0.15f) else Color.Transparent)
                            .clickable { tab = i }
                            .padding(vertical = 8.dp, horizontal = 4.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            d.icon, contentDescription = d.label,
                            tint = if (selected) Accent else InkFaint,
                            modifier = Modifier.size(22.dp)
                        )
                        Text(
                            d.label, fontSize = 10.sp,
                            color = if (selected) Accent else InkFaint
                        )
                    }
                }
            }

            // --- Main content area ---
            Box(Modifier.fillMaxSize().background(Panel2)) {
                when (tab) {
                    0 -> TodayScreen(
                        state = state,
                        onRefreshLocation = onRequestLocation,
                        onOpenMap = { tab = 1 }
                    )
                    1 -> MapScreenView(readings = state.readings, onMarkerClick = ::selectAndShowToday)
                    2 -> StationsScreen(readings = state.readings, onSelect = ::selectAndShowToday)
                    3 -> FaqScreen()
                }
            }
        }
    }
}
