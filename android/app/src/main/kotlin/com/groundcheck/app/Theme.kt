package com.groundcheck.app

import androidx.compose.material3.darkColorScheme
import androidx.compose.ui.graphics.Color

// Exact palette from desktop/index.html's :root[data-theme="dark"] block —
// this app is always dark, matching the desktop page's dark mode 1:1,
// never following system light/dark.
val SkyTop = Color(0xFF0C1A2B)
val SkyMid = Color(0xFF152B40)
val SkyBot = Color(0xFF1F3A52)
val Panel = Color(0xFF141F2A)
val Panel2 = Color(0xFF0A121A)
val Ink = Color(0xFFE8EEF4)
val InkDim = Color(0xFF8FA3B8)
val InkFaint = Color(0xFF5D7285)
val LineColor = Color(0xFF22323F)
val Accent = Color(0xFF5FCF95)

val GroundcheckColorScheme = darkColorScheme(
    primary = Accent,
    background = Panel2,
    surface = Panel,
    onBackground = Ink,
    onSurface = Ink,
    outline = LineColor,
    secondary = InkDim,
)
