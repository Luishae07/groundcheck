package com.groundcheck.app

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.drawable.BitmapDrawable
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.BoundingBox
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker

private fun circleBitmap(argb: Int, sizePx: Int = 36): Bitmap {
    val bmp = Bitmap.createBitmap(sizePx, sizePx, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bmp)
    val radius = sizePx / 2f
    val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = argb; style = Paint.Style.FILL }
    val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE; style = Paint.Style.STROKE; strokeWidth = 3f
    }
    canvas.drawCircle(radius, radius, radius - 2f, fill)
    canvas.drawCircle(radius, radius, radius - 2f, stroke)
    return bmp
}

@Composable
fun MapScreenView(readings: List<Reading>, onMarkerClick: (Reading) -> Unit) {
    AndroidView(
        modifier = Modifier.fillMaxSize(),
        factory = { context: Context ->
            MapView(context).apply {
                setTileSource(TileSourceFactory.MAPNIK) // OpenStreetMap
                setMultiTouchControls(true)
                controller.setZoom(5.5)
                controller.setCenter(GeoPoint(51.5, 10.5))
            }
        },
        update = { mapView ->
            mapView.overlays.clear()

            for (r in readings) {
                val marker = Marker(mapView)
                marker.position = GeoPoint(r.lat, r.lon)
                marker.title = "${r.id} — ${"%.1f".format(r.temp)}°C"
                marker.snippet = "Alt ${r.alt.toInt()} m"
                val c = tempColor(r.temp)
                val argb = Color.argb(255, (c.red * 255).toInt(), (c.green * 255).toInt(), (c.blue * 255).toInt())
                try {
                    marker.icon = BitmapDrawable(mapView.context.resources, circleBitmap(argb))
                } catch (_: Exception) { /* fall back to default pin if bitmap creation fails */ }
                marker.setOnMarkerClickListener { _, _ -> onMarkerClick(r); true }
                mapView.overlays.add(marker)
            }
            mapView.invalidate()

            // zoomToBoundingBox throws if called before the view has been
            // measured (width/height still 0) — that's the classic osmdroid
            // crash. Deferring with post{} guarantees a real layout pass has
            // happened, and we skip degenerate single-point bounding boxes.
            val distinct = readings.map { it.lat to it.lon }.distinct()
            if (distinct.size >= 2) {
                mapView.post {
                    try {
                        val points = readings.map { GeoPoint(it.lat, it.lon) }
                        mapView.zoomToBoundingBox(BoundingBox.fromGeoPoints(points), false, 50)
                    } catch (_: Exception) { /* best effort — keep default view if this fails */ }
                }
            }
        }
    )
}
