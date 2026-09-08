#!/usr/bin/env python3
"""Groundcheck data updater — fetches a window of radiosonde readings from
zeesen.mine.nu, merges into station_store.json (dedup-safe, never destructive),
and rebuilds data.json (ground-level, <=980m altitude) from the whole store.

Usage:
  python3 update.py --window 60        # last 60 seconds (run every minute)
  python3 update.py --window 86400     # last 1 day (run once daily)
  python3 update.py --days 200         # initial backfill, e.g. 200 days
"""
import argparse
import json
import datetime
import urllib.request
import os

BASE = os.path.dirname(os.path.abspath(__file__))
STORE_PATH = os.path.join(BASE, "station_store.json")
DATA_PATH = os.path.join(BASE, "data.json")
MAX_GROUND_ALT_M = 980


def log(msg):
    print(f"[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] {msg}", flush=True)


def fetch(window_seconds):
    url = f"https://zeesen.mine.nu/sondes.php?last={window_seconds}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    timeout = max(30, window_seconds // 1000)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    log(f"fetched zeesen (last={window_seconds}s) -> {len(data)} bytes")
    return json.loads(data)


def merge(store, raw):
    added = 0
    for serial, v in raw.items():
        temp = v.get("temp")
        if temp is None or temp < 0:
            continue
        tr = v.get("time_received")
        if not tr:
            continue
        lat, lon = v.get("lat"), v.get("lon")
        if lat is None or lon is None or (lat == 0 and lon == 0):
            continue
        key = f"{serial}|{tr}"
        if key not in store:
            store[key] = {
                "id": serial, "time": tr, "temp": temp, "alt": v.get("alt"),
                "pressure": v.get("pressure"), "humidity": v.get("humidity"),
                "lat": lat, "lon": lon, "source": [v.get("type")] if v.get("type") else None,
            }
            added += 1
    return added


def write_outputs(store):
    records = [r for r in store.values() if r.get("alt") is not None and r["alt"] <= MAX_GROUND_ALT_M]
    for r in records:
        r["tsunix"] = int(datetime.datetime.fromisoformat(r["time"].replace("Z", "+00:00")).timestamp())
    records.sort(key=lambda r: r["tsunix"], reverse=True)
    with open(DATA_PATH, "w") as out:
        json.dump(records, out, indent=2)
    return len(records)


def run(window_seconds):
    store = json.load(open(STORE_PATH)) if os.path.exists(STORE_PATH) else {}
    before = len(store)
    raw = fetch(window_seconds)
    added = merge(store, raw)
    with open(STORE_PATH, "w") as out:
        json.dump(store, out)
    total = write_outputs(store)
    log(f"store: {before} -> {len(store)} unique readings (+{added} new) -> {total} ground-level in data.json")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--window", type=int, help="fetch window in seconds")
    g.add_argument("--days", type=int, help="fetch window in days (for initial backfill)")
    args = p.parse_args()
    window = args.window if args.window is not None else args.days * 86400
    run(window)
