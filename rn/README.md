# Groundcheck — React Native (iOS)

The Groundcheck iOS app, built in React Native. Feature set: Today, Map, Stations, Account.

## What's here

This directory holds only the **app source** — `src/App.tsx`, the four screens under `src/screens/`, `src/api.ts`, and `package.json`. There's no native `ios/`/`android/` project checked in.

The native iOS project is generated fresh on every build, on the GitHub Actions macOS runner, by `.github/workflows/rn-ios-build.yml`:

1. `npx react-native init` scaffolds a bare RN project (this is what produces the `ios/` folder — Podfile, `.xcworkspace`, etc. — which only really works to generate on macOS)
2. This directory's `src/` and `package.json` dependencies are copied/merged into that scaffold
3. `npm install` + `pod install`
4. `xcodebuild` for a real device target (`generic/platform=iOS`), unsigned
5. The built `.app` is packaged into a standard IPA (`Payload/` zip) and uploaded as a workflow artifact

Unsigned on purpose — iLoader/AltStore-style sideloading tools sign on install themselves, so no Apple Developer certificate is needed in CI.

## Screens

- **Today** (`screens/TodayScreen.tsx`) — nearest station's current reading (temp, humidity, pressure, altitude), using device location via `@react-native-community/geolocation`.
- **Map** (`screens/MapScreen.tsx`) — all stations plotted on `react-native-maps`.
- **Stations** (`screens/StationsScreen.tsx`) — scrollable list of every station, most recent first.
- **Account** (`screens/AccountScreen.tsx`) — local nickname + device token, stored via `@react-native-async-storage/async-storage`. Device-only identity, no server accounts.

## Data source

`src/api.ts` never hardcodes a tunnel URL — Cloudflare quick tunnels get a new random hostname on every restart, so instead it fetches the current one at runtime from GitHub Pages:

- `https://luishae07.github.io/groundcheck/tunnel-url.txt` — backend data tunnel, used with `/apiinternel/dont/json/microsftwindowssucks/data` (the app's own unlimited endpoint — this is an official Groundcheck client, not a third party, so it doesn't use the rate-limited public `/api/data`)
- `https://luishae07.github.io/groundcheck/predictor-tunnel-url.txt` — predictor tunnel, used with `/predict`

If either backend tunnel restarts, only those two `.txt` files on GitHub Pages need updating — every client (this app included) picks up the new URL automatically on next fetch, no rebuild needed.

## Building locally

Requires a Mac with Xcode. This directory alone isn't a runnable project — either:

- Point a fresh `npx react-native init` scaffold at this `src/` the same way the CI workflow does, or
- Run the GitHub Actions workflow (`workflow_dispatch` on `rn-ios-build.yml`) and download the `Groundcheck-iOS-RN` artifact

## Why React Native

Matches how some other major apps (e.g. Discord) build their mobile clients.
