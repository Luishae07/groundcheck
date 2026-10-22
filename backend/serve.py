#!/usr/bin/env python3
import http.server
import socketserver
import time
import json
import os
import secrets
import bisect
import gzip
import threading

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("GROUNDCHECK_HTTP_PORT", 8765))

INTERNAL_PATH = "/apiinternel/dont/json/microsftwindowssucks/data"
INTERNAL_LITE_PATH = "/apiinternel/dont/json/microsftwindowssucks/lite"   # ?days=N : only the last N days (the pages load this)
PUBLIC_PATH = "/api/data"
KEYGEN_PATH = "/api/keys/new"
KEYS_FILE = os.path.join(BASE, "api_keys.json")

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

def is_rate_limited(bucket_id, max_reqs, window):
    now = time.time()
    hits = _rate_state.setdefault(bucket_id, [])
    hits[:] = [t for t in hits if now - t < window]
    if len(hits) >= max_reqs:
        return True
    hits.append(now)
    return False

# The last N days of data.json with only the fields the pages use, plain and gzipped. data.json is read again when it
# changes (a half-written file is skipped and the old data keeps being served); a range is rebuilt at most once a minute.
LITE_FIELDS = ("id", "time", "temp", "alt", "pressure", "humidity", "lat", "lon", "tsunix", "source")
_lite = {"mtime": None, "records": [], "ts": [], "built": {}}
_lite_lock = threading.Lock()

def _lite_load():
    path = os.path.join(BASE, "data.json")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return bool(_lite["records"])
    if _lite["mtime"] == mtime:
        return True
    try:
        with open(path) as f:
            recs = json.load(f)
    except (OSError, ValueError):
        return bool(_lite["records"])
    recs = [{k: r[k] for k in LITE_FIELDS if k in r} for r in recs]
    recs.sort(key=lambda r: r.get("tsunix", 0))
    _lite.update(mtime=mtime, records=recs, ts=[r.get("tsunix", 0) for r in recs], built={})
    return True

def _lite_body(days):
    with _lite_lock:
        if not _lite_load():
            return None
        hit = _lite["built"].get(days)
        if hit is None or time.time() - hit[0] > 60:
            recs = _lite["records"]
            if days:
                recs = recs[bisect.bisect_left(_lite["ts"], time.time() - days * 86400):]
            raw = json.dumps(recs, separators=(",", ":")).encode()
            hit = (time.time(), raw, gzip.compress(raw, 6))
            _lite["built"][days] = hit
        return hit

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

    def _serve_data_json(self):
        # The data is sent from a copy that is made once when data.json changes, not read again for every request.
        hit = _full_cached()
        if hit is None:
            self.send_error(404, "data.json not found")
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

    def _serve_lite(self):
        days = 7
        if "?" in self.path:
            for part in self.path.split("?", 1)[1].split("&"):
                if part.startswith("days="):
                    try:
                        days = max(0, min(5000, int(part[5:])))
                    except ValueError:
                        pass
        hit = _lite_body(days)
        if hit is None:
            self.send_error(404, "data.json not found")
            return
        gz = "gzip" in (self.headers.get("Accept-Encoding") or "")
        body = hit[2] if gz else hit[1]
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        if gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
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

    def do_POST(self):
        if self.path == KEYGEN_PATH:
            new_key = secrets.token_hex(16)
            _valid_keys[new_key] = {"created": time.time()}
            save_keys(_valid_keys)
            self._json(200, {
                "api_key": new_key,
                "limit": f"{KEY_MAX} requests / {KEY_WINDOW}s",
                "usage": "Pass it as header 'X-API-Key: <key>' or query '?key=<key>' on /api/data"
            })
            return
        self.send_error(404)

    def do_GET(self):
        base_path = self.path.split("?", 1)[0]

        if base_path == INTERNAL_PATH:
            # Unrestricted internal route — no rate limiting.
            self._serve_data_json()
            return

        if base_path == INTERNAL_LITE_PATH:
            self._serve_lite()
            return

        if base_path == PUBLIC_PATH:
            api_key = self._get_api_key()
            if api_key and api_key in _valid_keys:
                bucket, max_reqs, window = f"key:{api_key}", KEY_MAX, KEY_WINDOW
            else:
                bucket, max_reqs, window = f"ip:{self.client_address[0]}", DEFAULT_MAX, DEFAULT_WINDOW

            if is_rate_limited(bucket, max_reqs, window):
                self._json(429, {
                    "error": "rate_limited",
                    "message": f"Max {max_reqs} requests per {window}s for this tier. Try again shortly.",
                    "get_a_higher_limit": f"POST {KEYGEN_PATH} for a free API key ({KEY_MAX}/{KEY_WINDOW}s)."
                }, {"Retry-After": str(window)})
                return
            self._serve_data_json()
            return

        # Everything else falls through to normal static file serving.
        super().do_GET()

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    with Server(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Serving {BASE} on :{PORT}")
        print(f"Internal (unlimited): {INTERNAL_PATH}  and  {INTERNAL_LITE_PATH}?days=N")
        print(f"Public (default {DEFAULT_MAX}/{DEFAULT_WINDOW}s, keyed {KEY_MAX}/{KEY_WINDOW}s): {PUBLIC_PATH}")
        print(f"Get a key: POST {KEYGEN_PATH}")
        httpd.serve_forever()
