#!/usr/bin/env python3
import http.server
import socketserver
import time
import json
import os
import secrets
import hashlib

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 8765

INTERNAL_PATH = "/apiinternel/dont/json/microsftwindowssucks/data"
PUBLIC_PATH = "/api/data"
KEYGEN_PATH = "/api/keys/new"
KEYS_FILE = os.path.join(BASE, "api_keys.json")

# Default (no API key) limit
DEFAULT_MAX = 30
DEFAULT_WINDOW = 60

# API key tier limit
KEY_MAX = 9000
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
        path = os.path.join(BASE, "data.json")
        try:
            with open(path, "rb") as f:
                body = f.read()
        except FileNotFoundError:
            self.send_error(404, "data.json not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
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

        if base_path == PUBLIC_PATH:
            api_key = self._get_api_key()
            client_ip = self._real_client_ip()
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

            summary = {
                "created": _valid_keys[api_key].get("created"),
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
    with Server(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Serving {BASE} on :{PORT}")
        print(f"Internal (unlimited): {INTERNAL_PATH}")
        print(f"Public (default {DEFAULT_MAX}/{DEFAULT_WINDOW}s, keyed {KEY_MAX}/{KEY_WINDOW}s): {PUBLIC_PATH}")
        print(f"Get a key: POST {KEYGEN_PATH}")
        httpd.serve_forever()
