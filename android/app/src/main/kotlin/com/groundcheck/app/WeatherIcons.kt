package com.groundcheck.app

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.CloudQueue
import androidx.compose.material.icons.filled.Grain
import androidx.compose.material.icons.filled.Umbrella
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector

fun iconFor(c: SkyCondition): ImageVector = when (c) {
    SkyCondition.STORM -> Icons.Filled.Bolt
    SkyCondition.RAIN -> Icons.Filled.Umbrella
    SkyCondition.SHOWERS -> Icons.Filled.Grain
    SkyCondition.CLEAR -> Icons.Filled.WbSunny
    SkyCondition.PARTLY_CLOUDY -> Icons.Filled.CloudQueue
    SkyCondition.CLOUDY -> Icons.Filled.Cloud
}

fun tempColor(t: Double): Color = when {
    t < 3 -> Color(0xFF3B82C4)
    t < 7 -> Color(0xFF2F9E6F)
    t < 11 -> Color(0xFFC99A2E)
    else -> Color(0xFFC05A3C)
}
