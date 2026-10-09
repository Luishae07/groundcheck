#!/usr/bin/env python3
"""Groundcheck self-host installer. Needs only Python 3 (no git, no tar, no unzip, no Docker).

    curl -sL 192.168.1.27/gc | python3 -                 # installs into ./groundcheck, then asks a few questions
    curl -sL 192.168.1.27/gc | python3 - mydir           # a different folder
    python3 install.py --no-start                        # only download (when saved as a file)
"""
import io
import os
import subprocess
import sys
import urllib.request
import zipfile

URL = "https://github.com/Luishae07/groundcheck/archive/refs/heads/main.zip"
PREFIX = "groundcheck-main/backend/"
LAUNCHER = "groundcheck-main/selfhost/run.py"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    start = "--no-start" not in sys.argv
    dest = os.path.abspath(args[0] if args else "groundcheck")

    print("Downloading Groundcheck...")
    req = urllib.request.Request(URL, headers={"User-Agent": "groundcheck-selfhost-installer"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()

    n = 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            if info.filename == LAUNCHER:
                rel = "run.py"
            elif info.filename.startswith(PREFIX):
                rel = info.filename[len(PREFIX):]
            else:
                continue
            target = os.path.normpath(os.path.join(dest, rel))
            if not target.startswith(dest + os.sep):  # never write outside the folder
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(z.read(info))
            n += 1
    if n == 0:
        sys.exit("The download did not contain the backend folder.")
    print(f"Installed {n} files in {dest}")

    if not start:
        return
    print("\nStarting the setup...\n")
    os.chdir(dest)
    cmd = [sys.executable, "run.py"]
    stdin = None
    if not sys.stdin.isatty():  # run as "curl ... | python3 -": the questions must read the keyboard
        try:
            stdin = open("CON" if os.name == "nt" else "/dev/tty")
        except OSError:
            pass
    try:
        sys.exit(subprocess.call(cmd, stdin=stdin))
    except FileNotFoundError:
        print(f"Could not start it. Run it by hand: cd {dest} && python3 run.py")


if __name__ == "__main__":
    main()
