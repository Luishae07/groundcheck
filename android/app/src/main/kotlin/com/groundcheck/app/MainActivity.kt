package com.groundcheck.app

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.webkit.GeolocationPermissions
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var errorView: LinearLayout

    // Desktop page — full feature parity (map, predictor, stations grid),
    // and its layout already adapts down to phone width, so one URL covers
    // both phones and tablets instead of maintaining a separate mobile path.
    private val appUrl = "https://senate-armed-detector-farmers.trycloudflare.com/desktop/"

    private var pendingGeoOrigin: String? = null
    private var pendingGeoCallback: GeolocationPermissions.Callback? = null

    private val locationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        pendingGeoCallback?.invoke(pendingGeoOrigin, granted, false)
        pendingGeoOrigin = null
        pendingGeoCallback = null
        if (granted) scheduleWeatherAlerts()
    }

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { /* granted or not — worker checks itself before posting */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = FrameLayout(this)
        swipeRefresh = SwipeRefreshLayout(this)
        webView = WebView(this)

        // --- Fix: SwipeRefreshLayout was eating scroll gestures meant for
        // the page itself, making in-page scrolling feel broken. Only allow
        // pull-to-refresh to trigger when the WebView is scrolled to the
        // very top — otherwise let the WebView handle the gesture.
        swipeRefresh.setOnChildScrollUpCallback { _, _ -> webView.scrollY > 0 }

        swipeRefresh.addView(
            webView,
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT
        )
        root.addView(swipeRefresh, FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT)

        errorView = buildErrorView()
        errorView.visibility = View.GONE
        root.addView(errorView, FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT)

        setContentView(root)

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            setGeolocationEnabled(true)
            mediaPlaybackRequiresUserGesture = false
            useWideViewPort = true
            loadWithOverviewMode = true
        }

        webView.setBackgroundColor(Color.parseColor("#0A121A")) // desktop's --panel-2 dark bg — avoids a white flash before CSS loads

        webView.webViewClient = object : WebViewClient() {
            override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                errorView.visibility = View.GONE
                swipeRefresh.visibility = View.VISIBLE
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                swipeRefresh.isRefreshing = false
                // Force dark mode to match the desktop page's own explicit
                // dark palette, regardless of system light/dark setting —
                // the page's CSS already supports this via [data-theme].
                view?.evaluateJavascript(
                    "document.documentElement.setAttribute('data-theme','dark');", null
                )
            }

            override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
                super.onReceivedError(view, request, error)
                if (request?.isForMainFrame == true) {
                    swipeRefresh.isRefreshing = false
                    swipeRefresh.visibility = View.GONE
                    errorView.visibility = View.VISIBLE
                }
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onGeolocationPermissionsShowPrompt(
                origin: String?,
                callback: GeolocationPermissions.Callback?
            ) {
                val hasFine = ContextCompat.checkSelfPermission(
                    this@MainActivity, Manifest.permission.ACCESS_FINE_LOCATION
                ) == PackageManager.PERMISSION_GRANTED

                if (hasFine) {
                    callback?.invoke(origin, true, false)
                    scheduleWeatherAlerts()
                } else {
                    pendingGeoOrigin = origin
                    pendingGeoCallback = callback
                    locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
                }
            }
        }

        swipeRefresh.setOnRefreshListener { webView.reload() }

        webView.loadUrl(appUrl)

        // Non-deprecated back handling: go back through WebView history first.
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) webView.goBack() else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })

        requestNotificationPermissionIfNeeded()
    }

    private fun buildErrorView(): LinearLayout {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = android.view.Gravity.CENTER
            setBackgroundColor(Color.parseColor("#0A121A"))
        }
        val messageView = TextView(this).apply {
            text = "Can't reach Groundcheck right now.\nCheck your connection and try again."
            setTextColor(Color.parseColor("#E8EEF4"))
            gravity = android.view.Gravity.CENTER
            textSize = 15f
            setPadding(48, 0, 48, 32)
        }
        val retryBtn = Button(this).apply {
            text = "Retry"
            setOnClickListener {
                errorView.visibility = View.GONE
                swipeRefresh.visibility = View.VISIBLE
                webView.reload()
            }
        }
        layout.addView(messageView)
        layout.addView(retryBtn)
        return layout
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            val granted = ContextCompat.checkSelfPermission(
                this, Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
            if (!granted) notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    private fun scheduleWeatherAlerts() {
        // Checks every 30 minutes (WorkManager's practical minimum for
        // periodic work is 15 min) whether rain/thunderstorms are
        // happening or predicted soon near your last known location.
        val request = PeriodicWorkRequestBuilder<WeatherCheckWorker>(30, TimeUnit.MINUTES).build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "weather_alerts", ExistingPeriodicWorkPolicy.KEEP, request
        )
    }

    override fun onDestroy() {
        (webView.parent as? ViewGroup)?.removeView(webView)
        webView.destroy()
        super.onDestroy()
    }
}
