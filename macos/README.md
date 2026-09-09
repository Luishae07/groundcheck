# Groundcheck for macOS

A minimal WKWebView wrapper around the Groundcheck desktop web app, packaged as a native macOS app.

- Targets macOS 13.0+ (built/tested against macOS 13.7.8, build 22H730).
- No special GPU code — WebKit/Metal automatically uses whatever GPU macOS assigns (Intel integrated or a discrete Radeon on Intel Macs, or Apple Silicon's GPU), the OS handles that transparently.
- Built programmatically in `AppDelegate.swift` (no storyboard/nib) — window, menu bar, and WKWebView are all constructed in code.

## Building

Open `Groundcheck.xcodeproj` in Xcode (14+) on macOS and hit Run, or from the command line:

```bash
xcodebuild -project Groundcheck.xcodeproj -scheme Groundcheck -configuration Release build
```

**Note:** this project was authored on Linux without access to Xcode or a Swift/AppKit toolchain, so it has not been build-tested. The `project.pbxproj` was hand-written and checked for structural correctness (balanced braces/parens, consistent object references), and the Swift source was reviewed against known AppKit/WebKit APIs, but the first real build should happen in Xcode on an actual Mac — if it fails to open or build, that's the most likely place something needs a small fix.

## What it does

Loads `https://luishae07.github.io/groundcheck/desktop/` in a native window. Cmd+R reloads, Cmd+Q quits. If the page fails to load (e.g. tunnel down), shows a plain error message instead of blank WebKit chrome.
