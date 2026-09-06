package com.groundcheck.app

import android.Manifest
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Help
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Place
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
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
        Configuration.getInstance().userAgentValue = packageName

        viewModel.loadData()

        setContent {
            MaterialTheme {
                Surface {
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
        // No cached fix — request a fresh one.
        try {
            lm.requestSingleUpdate(LocationManager.GPS_PROVIDER, { loc ->
                viewModel.locateNearest(loc.latitude, loc.longitude)
            }, mainLooper)
        } catch (_: Exception) { }
    }
}

@Composable
fun AppRoot(viewModel: WeatherViewModel, onRequestLocation: () -> Unit) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var tab by remember { mutableIntStateOf(0) }

    Scaffold(
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    selected = tab == 0, onClick = { tab = 0 },
                    icon = { Icon(Icons.Filled.WbSunny, contentDescription = null) },
                    label = { Text("Today") }
                )
                NavigationBarItem(
                    selected = tab == 1, onClick = { tab = 1 },
                    icon = { Icon(Icons.Filled.Map, contentDescription = null) },
                    label = { Text("Map") }
                )
                NavigationBarItem(
                    selected = tab == 2, onClick = { tab = 2 },
                    icon = { Icon(Icons.Filled.Place, contentDescription = null) },
                    label = { Text("Stations") }
                )
                NavigationBarItem(
                    selected = tab == 3, onClick = { tab = 3 },
                    icon = { Icon(Icons.Filled.Help, contentDescription = null) },
                    label = { Text("FAQ") }
                )
            }
        }
    ) { padding ->
        androidx.compose.foundation.layout.Box(Modifier.padding(padding)) {
            when (tab) {
                0 -> TodayScreen(state = state, onRefreshLocation = onRequestLocation)
                1 -> MapScreenView(readings = state.readings, onMarkerClick = { })
                2 -> StationsScreen(readings = state.readings, onSelect = { })
                3 -> FaqScreen()
            }
        }
    }
}
