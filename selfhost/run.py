#!/usr/bin/env python3
"""Groundcheck backend launcher in plain Python (no bash, no cron): asks a few questions, fetches the
first data, then runs the web server, the live feed and the automatic radiosonde updates until Ctrl+C.

    python3 run.py            # asks the questions
    python3 run.py --yes      # all defaults, no questions
"""
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
YES = "--yes" in sys.argv


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
    http_port = ask("Web / data API port", "8765")
    ws_port = ask("Live-feed port", "8766")
    max_alt = ask("Max ground-level altitude filter in meters", "980")
    env = dict(os.environ, GROUNDCHECK_HTTP_PORT=http_port, GROUNDCHECK_WS_PORT=ws_port, GROUNDCHECK_MAX_ALT_M=max_alt)
    py = sys.executable

    if not os.path.exists("data.json"):
        days = ask("No data yet. How many days of radiosonde history to fetch first", "10")
        print(f"Fetching the last {days} day(s); large ranges take a while...")
        if subprocess.call([py, "update.py", "--days", days], env=env) != 0:
            print("The first fetch failed. Check your internet connection and run this again.")
            sys.exit(1)
    auto = yn("Keep the data up to date automatically while this runs?", "y")
    browser = yn("Open the app in your browser?", "n")

    procs = []
    def start(script, log):
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
            with open("update.log", "ab") as f:
                subprocess.call([py, "update.py", "--window", window], env=env, stdout=f, stderr=f)
    if auto:
        threading.Thread(target=updater, daemon=True).start()

    ip = lan_ip()
    print(f"\nGroundcheck is running:\n  http://localhost:{http_port}/\n  http://{ip}:{http_port}/   (other devices on your network)")
    print("Logs: serve.log, ws_proxy.log, update.log.   Press Ctrl+C to stop.")
    if browser:
        webbrowser.open(f"http://localhost:{http_port}/")
    try:
        while all(p.poll() is None for p in procs[:1]):
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
