#!/usr/bin/env python3
import http.server
import socketserver
import time
import json
import os
import secrets
import hashlib
import ipaddress
import gzip
import threading
import bisect
import math
import urllib.parse
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("GROUNDCHECK_HTTP_PORT", 8765))

INTERNAL_PATH = "/apiinternel/dont/json/microsftwindowssucks/data"
# the lean version for the website: only the last N days and only the fields the pages draw (?days=7, 0 = everything)
WHEREAMI_PATH = "/api/whereami"
try:
    import maxminddb
    _GEO = maxminddb.open_database(os.path.join(os.path.dirname(os.path.abspath(__file__)), "geo", "dbip.mmdb"))
except Exception:
    _GEO = None
INTERNAL_LITE_PATH = "/apiinternel/dont/json/microsftwindowssucks/lite"
LITE_FIELDS = ("id", "time", "temp", "alt", "pressure", "humidity", "lat", "lon", "tsunix", "source")
_lite = {"mtime": None, "records": [], "ts": [], "gz": {}}
_lite_lock = threading.Lock()
LITE_PREBUILT = (1, 2, 7, 30, 90, 365, 0)  # ranges kept ready in memory, plain and gzipped


def _lite_build(days):
    records = _lite["records"]
    if days:
        records = records[bisect.bisect_left(_lite["ts"], time.time() - days * 86400):]
    raw = json.dumps(records, separators=(",", ":")).encode()
    return (time.time(), raw, gzip.compress(raw, 6))


def _lite_refresh():
    """Reload data.json when it changed and rebuild the common ranges. A half-written file is skipped; the old data keeps being served."""
    path = os.path.join(BASE, "data.json")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return False
    if _lite["mtime"] == mtime:
        return True
    with _lite_lock:
        if _lite["mtime"] == mtime:
            return True
        try:
            with open(path) as f:
                recs = json.load(f)
        except (OSError, ValueError):
            return bool(_lite["records"])
        recs = [{k: r[k] for k in LITE_FIELDS if k in r} for r in recs]
        recs.sort(key=lambda r: r.get("tsunix", 0))
        ts = [r.get("tsunix", 0) for r in recs]
        _lite["records"], _lite["ts"] = recs, ts
        gz = {d: _lite_build(d) for d in LITE_PREBUILT}
        _lite["gz"] = gz
        _lite["mtime"] = mtime
    return True


def _lite_loop():
    while True:
        try:
            _lite_refresh()
        except Exception:
            pass
        time.sleep(10)



# ---- /api/weather: the temperature at any coordinates, from the nearest radiosonde that reported near the ground
WEATHER_PATH = "/api/weather"
WEATHER_HOURS = 19  # only readings from the last 19 hours are used
_countries = {"list": None}


def _country_of(lat, lon):
    """Name of the country that contains the point (Natural Earth borders, point-in-polygon), or None over sea."""
    if _countries["list"] is None:
        try:
            with open(os.path.join(BASE, "geo", "countries.json")) as f:
                _countries["list"] = json.load(f)
        except (OSError, ValueError):
            _countries["list"] = []
    for c in _countries["list"]:
        b = c["b"]
        if lon < b[0] or lon > b[2] or lat < b[1] or lat > b[3]:
            continue
        inside = False  # even-odd over every ring, so holes (lakes, enclaves) count out
        for ring in c["r"]:
            j = len(ring) - 1
            for i in range(len(ring)):
                xi, yi, xj, yj = ring[i][0], ring[i][1], ring[j][0], ring[j][1]
                if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                    inside = not inside
                j = i
        if inside:
            return c["n"]
    # the borders are simplified, so a coast city can fall just outside: take a country whose border is within about 30 km
    best, best_d = None, 0.3
    cl = max(math.cos(math.radians(lat)), 0.2)
    for c in _countries["list"]:
        b = c["b"]
        if lon < b[0] - 0.5 or lon > b[2] + 0.5 or lat < b[1] - 0.5 or lat > b[3] + 0.5:
            continue
        for ring in c["r"]:
            for x, y in ring:
                d = math.hypot((x - lon) * cl, y - lat)
                if d < best_d:
                    best, best_d = c["n"], d
    return best


def _km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def _nearest_sonde(lat, lon):
    """The closest reading taken near the ground (under 1500 m) in the last 19 hours."""
    _lite_refresh()
    recs, ts = _lite["records"], _lite["ts"]
    cl = math.cos(math.radians(lat))
    best, best_d2 = None, 1e18
    lo = bisect.bisect_left(ts, time.time() - WEATHER_HOURS * 3600)
    for i in range(lo, len(recs)):
        r = recs[i]
        if r.get("temp") is None or r.get("alt") is None or r["alt"] > 1500 or r.get("lat") is None or r.get("lon") is None:
            continue
        dlon = abs(r["lon"] - lon)
        dlon = min(dlon, 360 - dlon)
        d2 = (r["lat"] - lat) ** 2 + (dlon * cl) ** 2
        if d2 < best_d2:
            best, best_d2 = r, d2
    return best


def weather_answer(lat, lon):
    r = _nearest_sonde(lat, lon)
    if r is None:
        return 404, {"error": "no_data", "message": f"No near-ground reading from the last {WEATHER_HOURS} hours is available."}
    t = round(float(r["temp"]), 1)
    return 200, {
        "temp": f"{t}C",
        "temp_c": t,
        "radiosonde_used": r.get("id"),
        "coordinates_picked": f"{lat:g} {lon:g}",
        "country_coordinates": _country_of(lat, lon) or "none (open sea or no country)",
        "distance_km": round(_km(lat, lon, r["lat"], r["lon"]), 1),
        "humidity": r.get("humidity"),
        "pressure": r.get("pressure"),
        "measured_at": datetime.datetime.fromtimestamp(r.get("tsunix", 0), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def parse_coordinates(text):
    """Accepts {"lat":52.18,"lon":13.43}, {"coordinates":"52.18 13.43"}, {"coordinates":[52.18,13.43]} or just: 52.18 13.43"""
    text = (text or "").strip()
    try:
        obj = json.loads(text)
    except ValueError:
        obj = text
    if isinstance(obj, dict):
        if "lat" in obj and ("lon" in obj or "lng" in obj):
            obj = [obj["lat"], obj.get("lon", obj.get("lng"))]
        else:
            obj = obj.get("coordinates", obj.get("coordinates_picked"))
    if isinstance(obj, str):
        obj = obj.replace(",", " ").split()
    if not isinstance(obj, (list, tuple)) or len(obj) != 2:
        return None
    try:
        lat, lon = float(obj[0]), float(obj[1])
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or lat != lat or lon != lon:
        return None
    return lat, lon


PUBLIC_PATH = "/api/data"
KEYGEN_PATH = "/api/keys/new"
KEYS_FILE = os.path.join(BASE, "api_keys.json")
KEY_SETTINGS_SCHEMA_FILE = os.path.join(BASE, "key_settings_schema.json")
KEY_SETTINGS_SCHEMA_PATH = "/api/keys/settings/schema"

def load_settings_schema():
    try:
        return json.load(open(KEY_SETTINGS_SCHEMA_FILE))
    except Exception:
        return {}

SETTINGS_SCHEMA = load_settings_schema()  # 300+ configurable per-key preferences

# Default (no API key) limit
DEFAULT_MAX = 30
DEFAULT_WINDOW = 60

# API key tier limit
KEY_MAX = 13000
KEY_WINDOW = 10

def load_keys():
    if os.path.exists(KEYS_FILE):
        try:
            return json.load(open(KEYS_FILE))
        except Exception:
            return {}
    return {}

def save_keys(keys):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)

_valid_keys = load_keys()  # key -> {"created": ts, "label": str}
_rate_state = {}  # bucket_id -> [timestamps]

BLOCKED_IPS_FILE = os.path.join(BASE, "blocked_ips.json")
_blocked_cache = {"mtime": None, "ips": []}

def load_blocked_ips():
    # Re-read only when the file changes, so edits take effect without a restart.
    # Entries may be single addresses or CIDR ranges.
    try:
        mtime = os.path.getmtime(BLOCKED_IPS_FILE)
    except OSError:
        return []
    if mtime != _blocked_cache["mtime"]:
        nets = []
        try:
            for entry in json.load(open(BLOCKED_IPS_FILE)):
                try:
                    nets.append(ipaddress.ip_network(str(entry).strip(), strict=False))
                except ValueError:
                    pass
        except (OSError, ValueError):
            pass
        _blocked_cache["ips"] = nets
        _blocked_cache["mtime"] = mtime
    return _blocked_cache["ips"]

def is_blocked(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in load_blocked_ips())

BLOCKED_UA_FILE = os.path.join(BASE, "blocked-user-agents.json")
_blocked_ua_cache = {"mtime": None, "names": []}

def load_blocked_user_agents():
    try:
        mtime = os.path.getmtime(BLOCKED_UA_FILE)
    except OSError:
        return []
    if mtime != _blocked_ua_cache["mtime"]:
        try:
            names = [str(x).strip().lower() for x in json.load(open(BLOCKED_UA_FILE)) if str(x).strip()]
        except (OSError, ValueError):
            names = []
        _blocked_ua_cache["names"] = names
        _blocked_ua_cache["mtime"] = mtime
    return _blocked_ua_cache["names"]

def is_blocked_user_agent(ua):
    ua = (ua or "").lower()
    return any(name in ua for name in load_blocked_user_agents())

# ---- changelog: the commits of the GitHub repository, kept for 15 minutes and served as JSON (/api/changelog)
CHANGELOG_TTL = 15 * 60
CHANGELOG_PER = 100
_changelog = {}          # page -> (time, {"commits": [...], "more": bool})
_changelog_lock = threading.Lock()
_CHANGELOG_SKIP = ("update tunnel", "add tunnel", "update accuracy", "add accuracy", "update predictor", "add predictor", "update api", "add api")

def _changelog_fetch(page):
    import urllib.request
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "groundcheck-changelog"}
    if os.environ.get("GITHUB_TOKEN"):  # optional: a token raises GitHub's rate limit
        headers["Authorization"] = "token " + os.environ["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/Luishae07/groundcheck/commits?per_page={CHANGELOG_PER}&page={page}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
        raw = json.load(r)
    commits = []
    for c in raw:
        msg = (c.get("commit", {}).get("message") or "").split("\n")[0].strip()
        if not msg or msg.lower().startswith(_CHANGELOG_SKIP):
            continue
        commits.append({"message": msg, "date": c["commit"]["author"]["date"], "url": c.get("html_url")})
    return {"commits": commits, "more": len(raw) >= CHANGELOG_PER}

def changelog_page(page, force=False):
    with _changelog_lock:
        hit = _changelog.get(page)
        if hit and not force and time.time() - hit[0] < CHANGELOG_TTL:
            return hit[1]
    try:
        data = _changelog_fetch(page)
    except Exception:
        return hit[1] if hit else None          # GitHub is down: keep serving the old copy
    with _changelog_lock:
        _changelog[page] = (time.time(), data)
    return data

def _changelog_loop():
    while True:
        try:
            changelog_page(1, force=True)
        except Exception:
            pass
        time.sleep(CHANGELOG_TTL)

# Bad scrapers are refused on EVERY page this server serves (the site and the data), not only the internal API.
# Unlike blocked-user-agents.json (internal API only), this list holds just the unwanted bots; search engines and
# the welcome AI assistants are not on it. Edit blocked-site-bots.json and it takes effect at once.
SITE_BOTS_FILE = os.path.join(BASE, "blocked-site-bots.json")
_site_bots_cache = {"mtime": None, "names": []}

def is_site_bot(ua):
    try:
        mtime = os.path.getmtime(SITE_BOTS_FILE)
    except OSError:
        return False
    if mtime != _site_bots_cache["mtime"]:
        try:
            names = [str(x).strip().lower() for x in json.load(open(SITE_BOTS_FILE)) if str(x).strip()]
        except (OSError, ValueError):
            names = []
        _site_bots_cache["names"] = names
        _site_bots_cache["mtime"] = mtime
    ua = (ua or "").lower()
    return any(name in ua for name in _site_bots_cache["names"])

KEY_IP_LOGS_DIR = os.path.join(BASE, "key_ip_logs")
os.makedirs(KEY_IP_LOGS_DIR, exist_ok=True)
KEY_STATS_PREFIX = "/api/keys/"
KEY_STATS_SUFFIX = "/stats"

def is_rate_limited(bucket_id, max_reqs, window):
    now = time.time()
    hits = _rate_state.setdefault(bucket_id, [])
    hits[:] = [t for t in hits if now - t < window]
    if len(hits) >= max_reqs:
        return True
    hits.append(now)
    return False

def key_log_path(api_key):
    # Filename is derived from a hash of the key (sha512, cut to the first
    # 16 bytes / 32 hex chars) rather than the raw key itself, so directory
    # listings of key_ip_logs/ never expose a usable API key.
    h = hashlib.sha512(api_key.encode()).digest()[:16].hex()
    return os.path.join(KEY_IP_LOGS_DIR, f"{h}-all-ips.json")

def record_key_usage(api_key, ip, detail):
    path = key_log_path(api_key)
    try:
        log = json.load(open(path)) if os.path.exists(path) else {"total": 0, "ips": {}}
    except Exception:
        log = {"total": 0, "ips": {}}
    log["total"] = log.get("total", 0) + 1
    ip_hits = log["ips"].setdefault(ip, [])
    ip_hits.append(detail)
    # Keep each IP's hit list bounded so a key hammered from one address
    # can't make this file grow unbounded.
    if len(ip_hits) > 200:
        log["ips"][ip] = ip_hits[-200:]
    with open(path, "w") as f:
        json.dump(log, f)

def load_key_usage(api_key):
    path = key_log_path(api_key)
    if not os.path.exists(path):
        return {"total": 0, "ips": {}}
    try:
        return json.load(open(path))
    except Exception:
        return {"total": 0, "ips": {}}

def resolve_key_settings(api_key):
    """Merges a key's stored setting overrides onto the schema's defaults,
    so callers always get a complete settings dict regardless of what the
    key holder has actually customized."""
    stored = _valid_keys.get(api_key, {}).get("settings", {})
    return {name: stored.get(name, spec["default"]) for name, spec in SETTINGS_SCHEMA.items()}

PER_FIELD_SETTINGS_FIELDS = ["temp", "humidity", "pressure", "altitude"]

def apply_settings_to_records(records, s):
    """Every one of these 30 settings actually transforms the response —
    no inert/decorative entries. Defaults are all None/False, which are
    genuine no-ops, so an unconfigured key's response is identical to
    before this existed."""
    now = time.time()
    out = []
    for r in records:
        rec = dict(r)
        skip = False
        for f in PER_FIELD_SETTINGS_FIELDS:
            val = rec.get(f)
            if val is None:
                if s.get(f"{f}_hide_if_null"):
                    skip = True
                    break
                continue
            if not isinstance(val, (int, float)):
                continue
            min_t = s.get(f"{f}_min_threshold")
            if min_t is not None and val < min_t:
                skip = True
                break
            max_t = s.get(f"{f}_max_threshold")
            if max_t is not None and val > max_t:
                skip = True
                break
            if f == "temp" and s.get("temp_invert_sign"):
                val = -val
            if f == "temp" and s.get("temp_convert_units"):
                val = val * 9 / 5 + 32  # C -> F
            if f == "temp" and s.get("temp_round_to_integer"):
                val = round(val)
            else:
                dp = s.get(f"{f}_decimal_places")
                if dp is not None:
                    val = round(val, int(dp))
            rec[f] = val
        if skip:
            continue

        lat, lon = rec.get("lat"), rec.get("lon")
        if lat is not None:
            if s.get("min_lat") is not None and lat < s["min_lat"]:
                continue
            if s.get("max_lat") is not None and lat > s["max_lat"]:
                continue
        if lon is not None:
            if s.get("min_lon") is not None and lon < s["min_lon"]:
                continue
            if s.get("max_lon") is not None and lon > s["max_lon"]:
                continue

        if s.get("max_age_hours") is not None:
            ts = rec.get("tsunix") or 0
            if now - ts > s["max_age_hours"] * 3600:
                continue

        if s.get("strip_null_fields"):
            rec = {k: v for k, v in rec.items() if v is not None}
        out.append(rec)

    if s.get("dedupe_by_station"):
        seen = {}
        for rec in out:
            rid = rec.get("id")
            if rid not in seen or (rec.get("tsunix") or 0) > (seen[rid].get("tsunix") or 0):
                seen[rid] = rec
        out = list(seen.values())

    if s.get("sort_by_time_desc"):
        out.sort(key=lambda r: r.get("tsunix") or 0, reverse=True)

    if s.get("limit_results") is not None:
        out = out[: int(s["limit_results"])]

    if s.get("include_metadata"):
        return {
            "metadata": {"count": len(out), "generated_at": time.time()},
            "readings": out,
        }
    return out


# ---- the full data, ready to send (rebuilt only when data.json changes)
_full = {"key": None, "body": None, "gz": None}
_full_lock = threading.Lock()


def _full_cached():
    path = os.path.join(BASE, "data.json")
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = (st.st_mtime_ns, st.st_size)
    with _full_lock:
        if _full["key"] == key and _full["body"] is not None:
            return _full
        for _ in range(4):  # a writer may be replacing the file right now
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                json.loads(raw)  # once per change: make sure the file is complete
                break
            except (json.JSONDecodeError, OSError):
                time.sleep(0.5)
        else:
            return _full if _full["body"] is not None else None  # keep serving the last good copy
        _full["body"], _full["gz"], _full["key"] = raw, gzip.compress(raw, 4), key
        return _full



# ---- the data after the settings of an API key were applied, kept per settings until data.json changes
_set_cache = {}
_set_lock = threading.Lock()


def _settings_cached(settings):
    path = os.path.join(BASE, "data.json")
    try:
        st = os.stat(path)
    except OSError:
        return None
    dkey = (st.st_mtime_ns, st.st_size)
    skey = json.dumps(settings, sort_keys=True, default=str)
    with _set_lock:
        hit = _set_cache.get(skey)
        if hit and hit[2] == dkey:
            return hit
        for _ in range(4):  # a writer may be replacing the file right now
            try:
                with open(path) as f:
                    records = json.load(f)
                break
            except FileNotFoundError:
                return None
            except json.JSONDecodeError:
                time.sleep(0.5)
        else:
            return hit  # keep serving the last good copy, or nothing if there is none
        records = apply_settings_to_records(records, settings)
        indent = 2 if settings.get("pretty_print") else None
        body = json.dumps(records, indent=indent).encode()
        hit = (body, gzip.compress(body, 4), dkey)
        if len(_set_cache) >= 24:  # a few different settings are in use at once; forget the oldest
            _set_cache.pop(next(iter(_set_cache)))
        _set_cache[skey] = hit
        return hit


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE, **kwargs)

    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {fmt % args}")

    def end_headers(self):
        # Applies to every response, including static file serving —
        # nothing from this server should ever be cached by a browser or
        # intermediate proxy, since the whole point is fresh data.
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        super().end_headers()

    def _json(self, status, obj, extra_headers=None):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _serve_data_json(self, resolved_settings=None):
        # The common case (no key settings that change the data) sends bytes that are ready: they are made once when data.json
        # changes, not once per visitor. Reading, parsing and writing 40 MB of JSON for every request was the real limit.
        if not resolved_settings:
            hit = _full_cached()
            if hit is None:
                self.send_error(503, "data.json is being updated, try again in a moment")
                return
            gz = "gzip" in (self.headers.get("Accept-Encoding") or "")
            body = hit["gz"] if gz else hit["body"]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            if gz:
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(body)
            return
        hit = _settings_cached(resolved_settings)
        if hit is None:
            self.send_error(503, "data.json is being updated, try again in a moment")
            return
        gz = "gzip" in (self.headers.get("Accept-Encoding") or "")
        body = hit[1] if gz else hit[0]
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        if gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _serve_lite(self):
        if not _lite["records"] and not _lite_refresh():
            self.send_error(404, "data.json not found")
            return
        days = 7
        if "?" in self.path:
            for part in self.path.split("?", 1)[1].split("&"):
                if part.startswith("days="):
                    try:
                        days = max(0, min(5000, int(part[5:])))
                    except ValueError:
                        pass
        # the common ranges are ready in memory (rebuilt in the background); other ranges are built once and kept
        hit = _lite["gz"].get(days)
        if hit is None:
            hit = _lite_build(days)
            _lite["gz"][days] = hit
        body = hit[1]
        gz = "gzip" in (self.headers.get("Accept-Encoding") or "")
        if gz:
            body = hit[2]
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        if gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=20")
        self.end_headers()
        self.wfile.write(body)

    def _get_api_key(self):
        # Accept either header "X-API-Key" or query string "?key=..."
        key = self.headers.get("X-API-Key")
        if key:
            return key.strip()
        if "?" in self.path:
            qs = self.path.split("?", 1)[1]
            for part in qs.split("&"):
                if part.startswith("key="):
                    return part[4:].strip()
        return None

    def _real_client_ip(self):
        # The Cloudflare tunnel terminates the connection locally, so
        # self.client_address is always 127.0.0.1 (the tunnel daemon), not
        # the actual visitor. Cloudflare passes the real IP through
        # CF-Connecting-IP; fall back to the leftmost X-Forwarded-For hop,
        # then finally the raw socket address if neither header is present
        # (e.g. a direct localhost request).
        cf_ip = self.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip.strip()
        xff = self.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        return self.client_address[0]

    def _request_detail(self):
        # Richer per-hit record — everything Cloudflare/the client actually
        # gives us for free on every request, not just a bare timestamp.
        return {
            "ts": time.time(),
            "path": self.path,
            "method": self.command,
            "user_agent": self.headers.get("User-Agent"),
            "referer": self.headers.get("Referer"),
            "accept_language": self.headers.get("Accept-Language"),
            "cf_ray": self.headers.get("CF-Ray"),
            "cf_country": self.headers.get("CF-IPCountry"),
            "cf_connecting_ip": self.headers.get("CF-Connecting-IP"),
            "x_forwarded_for": self.headers.get("X-Forwarded-For"),
            "host": self.headers.get("Host"),
            "protocol": self.request_version,
        }

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return {}

    def do_OPTIONS(self):
        # Browser preflight: pages on luishae07.github.io POST JSON here (key settings), which needs this answer first.
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, QUERY, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        base_path = self.path.split("?", 1)[0]

        if base_path == KEYGEN_PATH:
            new_key = secrets.token_hex(16)
            _valid_keys[new_key] = {"created": time.time()}
            save_keys(_valid_keys)
            self._json(200, {
                "api_key": new_key,
                "limit": f"{KEY_MAX} requests / {KEY_WINDOW}s",
                "usage": "Pass it as header 'X-API-Key: <key>' or query '?key=<key>' on /api/data"
            })
            return

        # Self-service settings — the key itself is the credential (same
        # pattern as /stats): POST /api/keys/<key>/settings {"label": "...",
        # "paused": true/false} to update, or POST /api/keys/<key>/revoke
        # to permanently delete it. No admin login needed since only
        # someone who already holds the key can name it in the URL.
        if base_path.startswith(KEY_STATS_PREFIX) and base_path.endswith("/settings"):
            api_key = base_path[len(KEY_STATS_PREFIX):-len("/settings")]
            if api_key not in _valid_keys:
                self._json(404, {"error": "unknown api key"})
                return
            body = self._read_json_body()
            if "label" in body:
                label = str(body["label"])[:80]
                _valid_keys[api_key]["label"] = label
            if "paused" in body:
                _valid_keys[api_key]["paused"] = bool(body["paused"])

            # Any of the 300+ schema-defined preferences (key_settings_schema.json)
            # can be set here too — type-checked against the schema, unknown
            # names rejected so this can't become an arbitrary-data dumping
            # ground.
            settings = _valid_keys[api_key].setdefault("settings", {})
            rejected = []
            for name, value in body.items():
                if name in ("label", "paused"):
                    continue
                spec = SETTINGS_SCHEMA.get(name)
                if spec is None:
                    rejected.append(name)
                    continue
                if spec["type"] == "bool":
                    settings[name] = bool(value)
                elif spec["type"] == "number":
                    if value is None:
                        settings[name] = None
                    else:
                        try:
                            settings[name] = float(value)
                        except (TypeError, ValueError):
                            rejected.append(name)

            save_keys(_valid_keys)
            resp = {"status": "ok", "key": _valid_keys[api_key]}
            if rejected:
                resp["rejected_unknown_settings"] = rejected
            self._json(200, resp)
            return

        if base_path.startswith(KEY_STATS_PREFIX) and base_path.endswith("/revoke"):
            api_key = base_path[len(KEY_STATS_PREFIX):-len("/revoke")]
            if api_key not in _valid_keys:
                self._json(404, {"error": "unknown api key"})
                return
            del _valid_keys[api_key]
            save_keys(_valid_keys)
            self._json(200, {"status": "revoked"})
            return

        self.send_error(404)

    def _refuse_site_bot(self):
        if not is_site_bot(self.headers.get("User-Agent")):
            return False
        body = b"402 Payment Required.\nScraping this site costs one (1) weather balloon. Send it by post.\n"
        self.send_response(402)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        return True

    def _weather_request(self, coords_text):
        client_ip = self._real_client_ip()
        if is_blocked(client_ip):
            self._json(403, {"error": "blocked"})
            return
        api_key = self._get_api_key()
        if api_key and api_key in _valid_keys and _valid_keys[api_key].get("paused"):
            self._json(403, {"error": "key_paused", "message": "This API key is paused. Resume it via POST /api/keys/<key>/settings."})
            return
        if api_key and api_key in _valid_keys:
            bucket, max_reqs, window = f"weather-key:{api_key}", KEY_MAX, KEY_WINDOW
        else:
            bucket, max_reqs, window = f"weather-ip:{client_ip}", DEFAULT_MAX, DEFAULT_WINDOW
        if is_rate_limited(bucket, max_reqs, window):
            self._json(429, {
                "error": "rate_limited",
                "message": f"Max {max_reqs} requests per {window}s for this tier. Try again shortly.",
                "get_a_higher_limit": f"POST {KEYGEN_PATH} for a free API key ({KEY_MAX}/{KEY_WINDOW}s)."
            }, {"Retry-After": str(window)})
            return
        coords = parse_coordinates(coords_text)
        if coords is None:
            self._json(400, {"error": "bad_coordinates", "message": "Send the coordinates as JSON, for example {\"lat\": 52.184, \"lon\": 13.432} (latitude -90 to 90, longitude -180 to 180)."})
            return
        status, obj = weather_answer(*coords)
        self._json(status, obj)

    def do_QUERY(self):
        # QUERY is a safe GET that carries a body: the coordinates travel in the body, not the address
        if self.path.split("?", 1)[0] != WEATHER_PATH:
            self.send_error(404, "Not found")
            return
        try:
            n = min(int(self.headers.get("Content-Length") or 0), 2048)
        except ValueError:
            n = 0
        self._weather_request(self.rfile.read(n).decode("utf-8", "replace") if n else "")

    def do_HEAD(self):
        if self._refuse_site_bot():
            return
        super().do_HEAD()

    def do_GET(self):
        if self._refuse_site_bot():
            return
        base_path = self.path.split("?", 1)[0]

        if base_path.lower().rstrip("/") == "/data.json":
            # the raw data file is not public: only /api/data (limits, keys) and the internal route serve it
            self.send_error(404, "Not found")
            return

        if base_path == "/api/changelog":
            page = 1
            if "?" in self.path:
                for part in self.path.split("?", 1)[1].split("&"):
                    if part.startswith("page="):
                        try:
                            page = max(1, min(50, int(part[5:])))
                        except ValueError:
                            pass
            data = changelog_page(page)
            if data is None:
                self._json(503, {"error": "GitHub could not be reached and there is no saved copy yet"})
            else:
                self._json(200, data, {"Cache-Control": "public, max-age=300"})
            return

        if base_path == "/api/visits":
            try:
                with open(os.path.join(BASE, "visits.txt")) as f:
                    n = int(f.read().strip() or 0)
            except Exception:
                n = 0
            self._json(200, {"visits": n}, {"Cache-Control": "no-store"})
            return

        if base_path == WHEREAMI_PATH:
            # approximate place of the visitor from the local DB-IP file; the IP is not stored or sent anywhere
            rec = None
            try:
                rec = _GEO.get(self._real_client_ip()) if _GEO else None
            except Exception:
                rec = None
            loc = (rec or {}).get("location") or {}
            if "latitude" not in loc or "longitude" not in loc:
                self._json(200, {"success": False})
                return
            names = lambda k: ((rec.get(k) or {}).get("names") or {}).get("en")
            subs = rec.get("subdivisions") or [{}]
            self._json(200, {"success": True, "latitude": loc["latitude"], "longitude": loc["longitude"],
                             "city": names("city"), "region": (subs[0].get("names") or {}).get("en"),
                             "country": names("country")}, {"Cache-Control": "no-store"})
            return

        if base_path in (INTERNAL_PATH, INTERNAL_LITE_PATH):
            # Unrestricted internal route — no rate limiting, but IPs/ranges in blocked_ips.json
            # and User-Agents in blocked-user-agents.json are refused.
            if is_blocked(self._real_client_ip()):
                self._json(403, {"error": "blocked", "message": "Nice try, robot. This IP has been banned from the weather. Go outside and check yourself."})
                return
            if is_blocked_user_agent(self.headers.get("User-Agent")):
                self._json(403, {"error": "blocked", "message": "We know you're a bot. The weather does not care about your feelings, but we do not serve bots here. Shoo."})
                return
            if base_path == INTERNAL_LITE_PATH:
                self._serve_lite()
                return
            self._serve_data_json()
            return

        if base_path == KEY_SETTINGS_SCHEMA_PATH:
            self._json(200, {"count": len(SETTINGS_SCHEMA), "schema": SETTINGS_SCHEMA})
            return

        if base_path == WEATHER_PATH:  # the same answer for a plain GET, e.g. /api/weather?lat=52.184&lon=13.432
            q = urllib.parse.parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            self._weather_request(json.dumps({"lat": (q.get("lat") or [""])[0], "lon": (q.get("lon") or [""])[0]}))
            return

        if base_path == PUBLIC_PATH:
            api_key = self._get_api_key()
            client_ip = self._real_client_ip()
            if api_key and api_key in _valid_keys and _valid_keys[api_key].get("paused"):
                self._json(403, {"error": "key_paused", "message": "This API key is paused. Resume it via POST /api/keys/<key>/settings."})
                return
            if api_key and api_key in _valid_keys:
                bucket, max_reqs, window = f"key:{api_key}", KEY_MAX, KEY_WINDOW
            else:
                bucket, max_reqs, window = f"ip:{client_ip}", DEFAULT_MAX, DEFAULT_WINDOW

            if is_rate_limited(bucket, max_reqs, window):
                self._json(429, {
                    "error": "rate_limited",
                    "message": f"Max {max_reqs} requests per {window}s for this tier. Try again shortly.",
                    "get_a_higher_limit": f"POST {KEYGEN_PATH} for a free API key ({KEY_MAX}/{KEY_WINDOW}s)."
                }, {"Retry-After": str(window)})
                return
            if api_key and api_key in _valid_keys:
                record_key_usage(api_key, client_ip, self._request_detail())
                self._serve_data_json(resolve_key_settings(api_key))
            else:
                self._serve_data_json()
            return

        # Self-service: GET /api/keys/<key>/stats — the key itself is the
        # credential (same pattern as passing it to /api/data), so anyone
        # holding a key can see its own usage/IPs, no separate admin login.
        if base_path.startswith(KEY_STATS_PREFIX) and base_path.endswith(KEY_STATS_SUFFIX):
            api_key = base_path[len(KEY_STATS_PREFIX):-len(KEY_STATS_SUFFIX)]
            if api_key not in _valid_keys:
                self._json(404, {"error": "unknown api key"})
                return
            usage = load_key_usage(api_key)
            ips = usage.get("ips", {})

            def hit_ts(hit):
                # Old log entries (pre-rich-logging) are bare floats;
                # newer ones are detail dicts with a "ts" field.
                return hit if isinstance(hit, (int, float)) else hit.get("ts", 0)

            def hit_detail(hit):
                return None if isinstance(hit, (int, float)) else hit

            stored_settings = _valid_keys[api_key].get("settings", {})
            full_settings = {
                name: stored_settings.get(name, spec["default"])
                for name, spec in SETTINGS_SCHEMA.items()
            }

            summary = {
                "created": _valid_keys[api_key].get("created"),
                "label": _valid_keys[api_key].get("label"),
                "paused": _valid_keys[api_key].get("paused", False),
                "settings": full_settings,
                "total_requests": usage.get("total", 0),
                "distinct_ips": len(ips),
                "ips": [
                    {
                        "ip": ip,
                        "requests": len(hits),
                        "last_seen": max(hit_ts(h) for h in hits),
                        "recent_requests": [
                            hit_detail(h) for h in sorted(hits, key=hit_ts, reverse=True)[:10]
                            if hit_detail(h) is not None
                        ],
                    }
                    for ip, hits in sorted(ips.items(), key=lambda kv: -max(hit_ts(h) for h in kv[1]))
                ],
                "limit": f"{KEY_MAX} requests / {KEY_WINDOW}s",
            }
            self._json(200, summary)
            return

        # Everything else falls through to normal static file serving.
        super().do_GET()

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    threading.Thread(target=_lite_loop, daemon=True).start()
    threading.Thread(target=_changelog_loop, daemon=True).start()
    with Server(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Serving {BASE} on :{PORT}")
        print(f"Internal (unlimited): {INTERNAL_PATH}")
        print(f"Public (default {DEFAULT_MAX}/{DEFAULT_WINDOW}s, keyed {KEY_MAX}/{KEY_WINDOW}s): {PUBLIC_PATH}")
        print(f"Get a key: POST {KEYGEN_PATH}")
        httpd.serve_forever()
