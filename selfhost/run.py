#!/usr/bin/env python3
"""Groundcheck backend launcher in plain Python (no bash, no cron): asks a few questions, fetches the
first data, then runs the web server, the live feed and the automatic radiosonde updates until Ctrl+C.

    python3 run.py            # asks the questions
    python3 run.py --yes      # all defaults, no questions
"""
import os
import runpy
import socket
import subprocess
import sys
import threading
import time
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
YES = "--yes" in sys.argv
# iPhone/iPad terminals (a-Shell) cannot start several programs at once, so everything runs inside this
# one Python process there. Force it anywhere with --inprocess.
INPROC = "--inprocess" in sys.argv or "/var/mobile" in os.path.realpath(os.path.expanduser("~"))
_argv_lock = threading.Lock()


def run_script(script, args, log=None, use_argv=False):
    """Run a script of the backend in this process, as if started with python3 script args.
    Only the updater takes command-line arguments, so only it holds the lock around sys.argv: the
    servers run for ever and must not keep the updater waiting."""
    try:
        if use_argv:
            with _argv_lock:
                old = sys.argv
                sys.argv = [script] + list(args)
                try:
                    runpy.run_path(script, run_name="__main__")
                finally:
                    sys.argv = old
        else:
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
    if INPROC:
        os.environ.update(env)
        print("(running everything inside one process)")

    if not os.path.exists("data.json"):
        days = ask("No data yet. How many days of radiosonde history to fetch first", "10")
        print(f"Fetching the last {days} day(s); large ranges take a while...")
        rc = run_script("update.py", ["--days", days], use_argv=True) if INPROC else subprocess.call([py, "update.py", "--days", days], env=env)
        if rc != 0:
            print("The first fetch failed. Check your internet connection and run this again.")
            sys.exit(1)
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
                run_script("update.py", ["--window", window], "update.log", use_argv=True)
                continue
            with open("update.log", "ab") as f:
                subprocess.call([py, "update.py", "--window", window], env=env, stdout=f, stderr=f)
    # a-Shell crashes (segmentation fault) when the updater's internet code runs in a background thread,
    # so in single-process mode the main thread does the updating itself, further down.
    if auto and not INPROC:
        threading.Thread(target=updater, daemon=True).start()

    ip = lan_ip()
    print(f"\nGroundcheck is running:\n  http://localhost:{http_port}/\n  http://{ip}:{http_port}/   (other devices on your network)")
    print("Logs: serve.log, ws_proxy.log, update.log.   Press Ctrl+C to stop.")
    if INPROC:
        print("Keep this app open on screen: iOS pauses it, and the server with it, when you leave.")
    if browser:
        webbrowser.open(f"http://localhost:{http_port}/")
    try:
        last_daily, next_run = 0.0, time.time() + 60
        while INPROC or all(p.poll() is None for p in procs[:1]):
            time.sleep(1)
            if INPROC and auto and time.time() >= next_run:
                window = "86400" if time.time() - last_daily > 86400 else "60"
                if window == "86400":
                    last_daily = time.time()
                run_script("update.py", ["--window", window], "update.log", use_argv=True)
                next_run = time.time() + 60
        print("The web server stopped; see serve.log.")
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()
