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
curl https://grants-governmental-wma-out.trycloudflare.com/api/data
```

Rate-limited (30 req/60s by default); `POST /api/keys/new` gets you a free key raising that to 9000 req/10s. Full docs in `apidocs/`.

For comparison, Apple's WeatherKit REST API is $0 for the first 500,000 calls/month, then ~$50 per million after that — $9,999.99/month at the 200M-calls tier. Groundcheck's API has no billing at any volume.

### MCP server

`backend/mcp_server.py` exposes the data over the Model Context Protocol (stdio JSON-RPC, no external deps) — tools include `current_reading`, `nearest_station`, `station_history`, `search_readings`, `predictor`, and `stats`. Point an `.mcp.json` config at it to query live radiosonde data from Claude Code or any other MCP client.

## Android

A Kotlin WebView wrapper for tablets, built in `android/` — sideloadable APK via GitHub Releases (not on the Play Store), with pull-to-refresh and background notifications for nearby rain/thunderstorm conditions.

## macOS

A native WKWebView wrapper in `macos/`, targeting macOS 13.0+. Open `Groundcheck.xcodeproj` in Xcode to build.

## Licence

- **AGPL-3.0** (see `LICENSE`): the whole repository, including the **Android app** (`android/`), the web app, the backend, the desktop and extension builds.
- **MIT** (see `ios/LICENSE`): only the **iOS app** (`ios/`).

The iOS app is MIT because AGPL/GPL-licensed code cannot be distributed through Apple's App Store under Apple's Terms of Service.

### Licence FAQ

_Click a question to open the answer._

<details>
<summary><b>Can I use Groundcheck for free?</b></summary>

Yes. You can use it for yourself, at work, or in a business, at no cost.

</details>

<details>
<summary><b>Can I run my own copy?</b></summary>

Yes. That is what the self-host guide is for. Running an unmodified copy needs nothing from you.

</details>

<details>
<summary><b>Do I have to share my changes?</b></summary>

Only if you let other people use your modified version. If you change the AGPL parts and give the program to others, or let them use it over a network (a website or an API), you must offer them the source code of your version under the AGPL too. If you change it only for yourself, you owe no one anything.

</details>

<details>
<summary><b>What does "over a network" mean?</b></summary>

It is the difference between the AGPL and the plain GPL. If people use your modified version through a website or a server, that counts like handing them a copy, so they are entitled to the source.

</details>

<details>
<summary><b>Can I sell it or charge for it?</b></summary>

Yes. The AGPL allows selling. The source-sharing rule above still applies to whoever gets it.

</details>

<details>
<summary><b>Can I use the code in my own closed-source app?</b></summary>

Not the AGPL parts. If you build them into your program, your program must be AGPL too. The `ios/` folder is MIT, so that part can go into closed-source apps as long as you keep its licence notice.

</details>

<details>
<summary><b>Does using the Groundcheck API make my app AGPL?</b></summary>

Generally no. Calling the API or reading its data is not copying the code, so your own app can have any licence. Copying the source code is what brings the AGPL in.

</details>

<details>
<summary><b>Can I put the Android app on Google Play or F-Droid?</b></summary>

Yes, as long as you also make the source of your version available under the AGPL.

</details>

<details>
<summary><b>Why is the iOS app MIT?</b></summary>

Apple's App Store terms do not work with AGPL/GPL code, so the iOS app uses the MIT licence. See `ios/LICENSE`.

</details>

<details>
<summary><b>I want to contribute. Which licence does my work get?</b></summary>

Changes to the AGPL parts are AGPL. Changes inside `ios/` are MIT.

</details>

<details>
<summary><b>Where is the full text?</b></summary>

In `LICENSE` (AGPL-3.0) and `ios/LICENSE` (MIT). This FAQ is a plain-language summary and not legal advice. If you are unsure, read the licence itself or ask a lawyer.

</details>
