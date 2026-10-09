#!/usr/bin/env python3
"""Groundcheck backend launcher in plain Python (no bash, no cron): asks a few questions, fetches the
first data, then runs the web server, the live feed and the automatic radiosonde updates until Ctrl+C.

    python3 run.py            # asks the questions
    python3 run.py --yes      # all defaults, no questions
"""
import hashlib
import os
import random
import string
import runpy
import socket
import subprocess
import sys
import threading
import time
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
YES = "--yes" in sys.argv


def pick_port(taken=()):
    """A fresh port on every launch: make a random 10-character string, hash it with SHA-256 and use
    the first four digits of the hash. Tries again if that is below 1024 or already in use."""
    while True:
        word = "".join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(10))
        digits = "".join(c for c in hashlib.sha256(word.encode()).hexdigest() if c.isdigit())[:4]
        port = int(digits)
        if port < 1024 or port in taken:
            continue
        try:
            probe = socket.socket()
            probe.bind(("", port))
            probe.close()
            return port
        except OSError:
            continue

# iPhone/iPad terminals (a-Shell) cannot start several programs at once, so everything runs inside this
# one Python process there. Force it anywhere with --inprocess.
INPROC = "--inprocess" in sys.argv or "/var/mobile" in os.path.realpath(os.path.expanduser("~"))
_argv_lock = threading.Lock()


def run_script(script, args, log=None):
    """Run a script of the backend in this process, as if started with python3 script args."""
    with _argv_lock:
        old = sys.argv
        sys.argv = [script] + list(args)
        try:
            runpy.run_path(script, run_name="__main__")
            return 0
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        except Exception as e:  # keep the other parts running
            msg = f"{script} stopped: {e!r}"
            print(msg)
            if log:
                with open(log, "a") as f:
                    f.write(msg + "\n")
            return 1
        finally:
            sys.argv = old


def ask(question, default):
    if YES:
        return default
    try:
        a = input(f"{question} [{default}]: ").strip()
    except EOFError:
        return default
    return a or default


def yn(question, default="y"):
    return ask(question + " (y/n)", default).lower().startswith("y")


MIRROR_URL = "http://192.168.1.27:8765/api/data"


def mirror_data():
    """Copy the full reading history from our home server instead of from the radiosonde source.
    The source only hands out the latest reading per balloon, so a phone that cannot poll every minute
    ends up with a thin, old slice; the home server has polled all along. Returns True on success."""
    url = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--mirror=")), MIRROR_URL)
    print(f"Copying the readings from {url} ...")
    try:
        import json
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "groundcheck-selfhost"})
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
        data = json.loads(raw)
        if not isinstance(data, list) or not data:
            raise ValueError("unexpected answer")
        with open("data.json.tmp", "wb") as f:
            f.write(raw)
        os.replace("data.json.tmp", "data.json")
        newest = max((x.get("time", "") for x in data if isinstance(x, dict)), default="?")
        print(f"Got {len(data)} readings, newest {newest}.")
        return True
    except Exception as e:
        print(f"Could not reach the home server ({e}); using the radiosonde source instead.")
        return False


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "your-ip"


def main():
    os.chdir(HERE)
    print("Groundcheck backend\n====================")
    # --port=8765 pins the ports (the live feed gets the next one), so a restarted server keeps its address
    fixed = next((int(a.split("=", 1)[1]) for a in sys.argv if a.startswith("--port=") and a.split("=", 1)[1].isdigit()), None)
    http_port = ask("Web / data API port", str(fixed or pick_port()))
    ws_port = ask("Live-feed port", str(fixed + 1 if fixed else pick_port({int(http_port)} if http_port.isdigit() else ())))
    max_alt = ask("Max ground-level altitude filter in meters", "980")
    env = dict(os.environ, GROUNDCHECK_HTTP_PORT=http_port, GROUNDCHECK_WS_PORT=ws_port, GROUNDCHECK_MAX_ALT_M=max_alt)
    py = sys.executable
    if INPROC:
        os.environ.update(env)
        print("(running everything inside one process)")

    mirrored = mirror_data() if (INPROC or "--mirror" in sys.argv or any(a.startswith("--mirror=") for a in sys.argv)) else False
    if mirrored:
        pass
    elif not os.path.exists("data.json"):
        days = ask("No data yet. How many days of radiosonde history to fetch first", "10")
        print(f"Fetching the last {days} day(s); large ranges take a while...")
        rc = run_script("update.py", ["--days", days]) if INPROC else subprocess.call([py, "update.py", "--days", days], env=env)
        if rc != 0:
            print("The first fetch failed. Check your internet connection and run this again.")
            sys.exit(1)
    else:
        # data already exists: catch up on everything since it was last updated (the updater only
        # merges new readings, so this is safe to repeat)
        age = int(time.time() - os.path.getmtime("data.json"))
        window = str(max(3600, min(age + 600, 90 * 86400)))
        print(f"Catching up on the readings since the last update ({int(window) // 3600} h)...")
        if INPROC:
            run_script("update.py", ["--window", window], "update.log")
        else:
            subprocess.call([py, "update.py", "--window", window], env=env)
    auto = yn("Keep the data up to date automatically while this runs?", "y")
    browser = yn("Open the app in your browser?", "n")

    procs = []
    def start(script, log):
        if INPROC:
            threading.Thread(target=run_script, args=(script, [], log), daemon=True).start()
            return
        f = open(log, "ab")
        procs.append(subprocess.Popen([py, script], env=env, stdout=f, stderr=f))
    start("serve.py", "serve.log")
    if os.path.exists("ws_proxy.py"):
        start("ws_proxy.py", "ws_proxy.log")

    stop = threading.Event()
    def updater():
        last_daily = 0.0
        while not stop.wait(60):
            window = "86400" if time.time() - last_daily > 86400 else "60"
            if window == "86400":
                last_daily = time.time()
            if INPROC:
                run_script("update.py", ["--window", window], "update.log")
                continue
            with open("update.log", "ab") as f:
                subprocess.call([py, "update.py", "--window", window], env=env, stdout=f, stderr=f)
    if auto:
        threading.Thread(target=updater, daemon=True).start()

    ip = lan_ip()
    print(f"\nGroundcheck is running:\n  http://localhost:{http_port}/\n  http://{ip}:{http_port}/   (other devices on your network)")
    print("Logs: serve.log, ws_proxy.log, update.log.   Press Ctrl+C to stop.")
    if INPROC:
        print("Keep this app open on screen: iOS pauses it, and the server with it, when you leave.")
    if browser:
        webbrowser.open(f"http://localhost:{http_port}/")
    try:
        while INPROC or all(p.poll() is None for p in procs[:1]):
            time.sleep(1)
        print("The web server stopped; see serve.log.")
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()
