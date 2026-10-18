#!/usr/bin/env python3
"""Groundcheck data updater. Fetches radiosonde readings from two sources and combines them:

  1. zeesen.mine.nu   - the main feed, any window (seconds to years)
  2. SondeHub         - sondehub.org, radiosonde telemetry from receivers worldwide (open API, no key)

Both are merged into station_store.json (dedup-safe, never destructive) and data.json (ground level,
<= 980 m altitude) is rebuilt from the whole store. A SondeHub reading is skipped when the store already has
the same sonde within 2 minutes (from zeesen or from an earlier SondeHub run).

SondeHub is a free volunteer service, so it is asked politely: at most once every 5 hours (the check is kept in
.sondehub_last next to this file), with a window of at least 6 hours so runs overlap and no landed sonde is
missed, and at most 4 days. A cron job that runs every minute therefore still only calls SondeHub a few times
a day. If one source fails, the other is still used.

Usage:
  python3 update.py --window 60                # last 60 seconds (run every minute)
  python3 update.py --window 86400             # last 1 day (run once daily)
  python3 update.py --days 200                 # initial backfill, e.g. 200 days (SondeHub adds its last 4 days)
  python3 update.py --window 60 --only zeesen  # use just one source (zeesen or sondehub)
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
STORE_PATH = os.path.join(BASE, "station_store.json")
DATA_PATH = os.path.join(BASE, "data.json")
SONDEHUB_STAMP = os.path.join(BASE, ".sondehub_last")
MAX_GROUND_ALT_M = int(os.environ.get("GROUNDCHECK_MAX_ALT_M", 980))
SONDEHUB_EVERY = 5 * 3600        # ask SondeHub at most this often (seconds)
SONDEHUB_MIN_WINDOW = 6 * 3600   # overlap between runs
SONDEHUB_MAX_WINDOW = 4 * 86400  # longest window asked from SondeHub
SAME_SONDE_SECONDS = 120         # the same sonde within this many seconds is the same reading


def log(msg):
    print(f"[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] {msg}", flush=True)


def get_json(url, user_agent, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ---- source 1: zeesen.mine.nu

def fetch_zeesen(window_seconds):
    url = f"https://zeesen.mine.nu/sondes.php?last={window_seconds}"
    data = get_json(url, "Mozilla/5.0", max(30, window_seconds // 1000))
    log(f"fetched zeesen (last={window_seconds}s) -> {len(data)} bytes")
    return json.loads(data)


def merge_zeesen(store, raw):
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


# ---- source 2: SondeHub

def unix(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def num(v, lo, hi):
    return v if isinstance(v, (int, float)) and lo <= v <= hi else None


def sondehub_due():
    try:
        return time.time() - float(open(SONDEHUB_STAMP).read().strip()) >= SONDEHUB_EVERY
    except (OSError, ValueError):
        return True


def fetch_sondehub(window_seconds):
    last = min(max(window_seconds, SONDEHUB_MIN_WINDOW), SONDEHUB_MAX_WINDOW)
    url = f"https://api.v2.sondehub.org/sondes?last={last}"
    data = get_json(url, "Groundcheck/1.0 (weather balloon readings)", 60)
    log(f"fetched SondeHub (last={last}s) -> {len(data)} bytes")
    raw = json.loads(data)
    with open(SONDEHUB_STAMP, "w") as f:
        f.write(str(time.time()))
    return raw


def merge_sondehub(store, raw):
    seen = {}  # serial -> times already in the store, from any source
    for r in store.values():
        try:
            seen.setdefault(r["id"], []).append(unix(r["time"]))
        except Exception:
            pass
    added = skipped = 0
    for serial, v in raw.items():
        alt = num(v.get("alt"), -50, MAX_GROUND_ALT_M)   # only sondes at ground level
        temp = num(v.get("temp"), 0, 60)                 # no sub-zero readings, same rule as the zeesen feed
        lat, lon = v.get("lat"), v.get("lon")
        dt = v.get("datetime")
        if alt is None or temp is None or not dt or lat is None or lon is None or (lat == 0 and lon == 0):
            continue
        t = unix(dt)
        if any(abs(t - x) < SAME_SONDE_SECONDS for x in seen.get(serial, [])):
            skipped += 1
            continue
        iso = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        store[f"{serial}|{iso}"] = {
            "id": serial, "time": iso, "temp": temp, "alt": alt,
            "pressure": num(v.get("pressure"), 100, 1100), "humidity": num(v.get("humidity"), 0, 100),
            "lat": lat, "lon": lon, "source": [x for x in (v.get("type"), "SondeHub") if x],
        }
        seen.setdefault(serial, []).append(t)
        added += 1
    return added, skipped


# ---- output

def write_outputs(store):
    records = [r for r in store.values() if r.get("alt") is not None and r["alt"] <= MAX_GROUND_ALT_M]
    for r in records:
        r["tsunix"] = int(datetime.datetime.fromisoformat(r["time"].replace("Z", "+00:00")).timestamp())
    records.sort(key=lambda r: r["tsunix"], reverse=True)
    with open(DATA_PATH, "w") as out:
        json.dump(records, out, indent=2)
    return len(records)


def save_store(store):
    tmp = STORE_PATH + ".tmp"           # write to a temporary file and rename, so a crash never leaves half a store
    with open(tmp, "w") as out:
        json.dump(store, out)
    os.replace(tmp, STORE_PATH)


def run(window_seconds, only, force_sondehub):
    store = json.load(open(STORE_PATH)) if os.path.exists(STORE_PATH) else {}
    before = len(store)
    ok = 0
    if only in (None, "zeesen"):
        try:
            added = merge_zeesen(store, fetch_zeesen(window_seconds))
            log(f"zeesen: +{added} new readings")
            ok += 1
        except Exception as e:
            log(f"zeesen failed: {e}")
    if only in (None, "sondehub"):
        if only == "sondehub" or force_sondehub or sondehub_due():
            try:
                added, skipped = merge_sondehub(store, fetch_sondehub(window_seconds))
                log(f"SondeHub: +{added} new ground readings, {skipped} already known")
                ok += 1
            except Exception as e:
                log(f"SondeHub failed: {e}")
        else:
            log("SondeHub: asked less than 5 hours ago, skipped this time")
    if ok == 0:
        log("no source answered; nothing changed")
        sys.exit(1)
    save_store(store)
    total = write_outputs(store)
    log(f"store: {before} -> {len(store)} unique readings -> {total} ground-level in data.json")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--window", type=int, help="fetch window in seconds")
    g.add_argument("--days", type=int, help="fetch window in days (for initial backfill)")
    p.add_argument("--only", choices=["zeesen", "sondehub"], help="use just one source")
    args = p.parse_args()
    window = args.window if args.window is not None else args.days * 86400
    run(window, args.only, force_sondehub=args.days is not None)
