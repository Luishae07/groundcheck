# Groundcheck

A weather app built on **real radiosonde (weather balloon) sensor data** — not a forecast model. Every number shown was actually measured by a sensor in the air, sourced from live [sonde.mine.nu](https://sonde.mine.nu) / [zeesen.mine.nu](https://zeesen.mine.nu) telemetry.

- **Live app:** https://luishae07.github.io/groundcheck/
- **Desktop view:** https://luishae07.github.io/groundcheck/desktop/
- **API docs:** https://luishae07.github.io/groundcheck/apidocs/

## What makes this different

Most weather apps show you a forecast — a model's prediction of what the atmosphere will probably do. Groundcheck shows you what a sensor actually measured, right now or recently, from a real weather balloon in flight. The one exception is the "Next hours" panel, which is built from this app's own 7-day historical diurnal pattern rather than an external forecast API.

Ground-level readings only (balloons spend most of a flight at altitude, where it's routinely far below freezing — not representative of surface weather), a live in-flight banner when the shown station is an actual balloon currently airborne, satellite maps with clustering, and history views from 7 days up to all-time.

See the in-app FAQ (desktop view) for the full rundown — 45 questions covering data, accuracy, the API, self-hosting, and the Android app.

## Repo layout

| Path | What it is |
|---|---|
| `index.html` | Mobile web app |
| `desktop/` | Desktop web app (fuller layout, search, FAQ) |
| `apidocs/` | Public API documentation page |
| `backend/` | Self-hostable backend — server, live-feed proxy, data updater, MCP server, and the frontend wired to run against your own instance |
| `android/` | Kotlin WebView wrapper for Android tablets |
| `macos/` | Swift/WebKit wrapper for macOS |

## Self-hosting

Everything needed to run your own instance lives in `backend/` — no database, no cloud dependency, just Python's standard library.

```bash
git clone https://github.com/Luishae07/groundcheck.git
cd groundcheck/backend
./start.sh
```

`start.sh` (Linux/Mac) walks you through: HTTP/WebSocket ports, the ground-level altitude filter, whether to bootstrap `data.json` with an initial history backfill (1 to 800 days), and whether to set up automatic radiosonde checks via cron (every minute, daily, or a custom interval). `start.ps1` does the same on Windows via PowerShell and Task Scheduler — if WSL with a Linux distro is installed, it offers to hand off to `start.sh` instead for the fuller experience.

## API

```bash
curl https://<your-tunnel-or-host>/api/data
```

Rate-limited (30 req/60s by default); `POST /api/keys/new` gets you a free key raising that to 9000 req/10s. Full docs in `apidocs/`.

For comparison, Apple's WeatherKit REST API is $0 for the first 500,000 calls/month, then ~$50 per million after that — $9,999.99/month at the 200M-calls tier. Groundcheck's API has no billing at any volume.

### MCP server

`backend/mcp_server.py` exposes the data over the Model Context Protocol (stdio JSON-RPC, no external deps) — tools include `current_reading`, `nearest_station`, `station_history`, `search_readings`, `predictor`, and `stats`. Point an `.mcp.json` config at it to query live radiosonde data from Claude Code or any other MCP client.

## Android

A Kotlin WebView wrapper for tablets, built in `android/` — sideloadable APK via GitHub Releases (not on the Play Store), with pull-to-refresh and background notifications for nearby rain/thunderstorm conditions.

## macOS

A native WKWebView wrapper in `macos/`, targeting macOS 13.0+. Open `Groundcheck.xcodeproj` in Xcode to build.
