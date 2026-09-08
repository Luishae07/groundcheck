#!/usr/bin/env bash
# Groundcheck backend launcher — serve.py (HTTP data API) + ws_proxy.py (live feed).
set -e
cd "$(dirname "$0")"

echo "Groundcheck backend"
echo "===================="

if [[ ! -f "data.json" ]]; then
  read -rp "data.json not found. Create it now? (y/n): " CREATE_DATA
  if [[ "$CREATE_DATA" =~ ^[Yy] ]]; then
    sleep 2
    echo "How many days of history should the initial fetch cover?"
    select DAYS in 50 200 500 600 800; do
      if [[ -n "$DAYS" ]]; then
        break
      fi
    done
    echo "Fetching last $DAYS day(s) of radiosonde history — this can take a while for large ranges..."
    python3 update.py --days "$DAYS"
    echo "data.json created."
  fi
fi

read -rp "Run in background with nohup? (y/n): " USE_NOHUP
read -rp "Enable logs? (y/n): " USE_LOGS

if [[ "$USE_LOGS" =~ ^[Yy] ]]; then
  SERVE_OUT="serve.log"
  WS_OUT="ws_proxy.log"
  UPDATE_OUT="update.log"
else
  SERVE_OUT="/dev/null"
  WS_OUT="/dev/null"
  UPDATE_OUT="/dev/null"
fi

# --- install cron jobs: check radiosonde data every minute and once a day ---
SCRIPT_DIR="$(pwd)"
if [[ "$UPDATE_OUT" == "/dev/null" ]]; then
  UPDATE_LOG_TARGET="/dev/null"
else
  UPDATE_LOG_TARGET="$SCRIPT_DIR/$UPDATE_OUT"
fi
CRON_MARKER="# groundcheck-backend-auto"
CRON_MIN="* * * * * cd $SCRIPT_DIR && python3 update.py --window 60 >> $UPDATE_LOG_TARGET 2>&1 $CRON_MARKER"
CRON_DAY="0 3 * * * cd $SCRIPT_DIR && python3 update.py --window 86400 >> $UPDATE_LOG_TARGET 2>&1 $CRON_MARKER"

if command -v crontab >/dev/null 2>&1; then
  ( crontab -l 2>/dev/null | grep -v "$CRON_MARKER" ; echo "$CRON_MIN" ; echo "$CRON_DAY" ) | crontab -
  echo "Installed cron jobs: radiosonde check every minute + once daily."
else
  echo "crontab not available — skipping automatic radiosonde checks (run update.py manually or via another scheduler)."
fi

if [[ "$USE_NOHUP" =~ ^[Yy] ]]; then
  nohup python3 serve.py > "$SERVE_OUT" 2>&1 < /dev/null &
  disown
  nohup python3 ws_proxy.py > "$WS_OUT" 2>&1 < /dev/null &
  disown
  echo "Started in background (nohup)."
else
  echo "Starting in foreground (this shell). Use two terminals for both servers,"
  echo "or press Ctrl+C and re-run choosing nohup to run both at once."
  python3 serve.py > "$SERVE_OUT" 2>&1 &
  SERVE_PID=$!
  python3 ws_proxy.py > "$WS_OUT" 2>&1 &
  WS_PID=$!
  trap "kill $SERVE_PID $WS_PID 2>/dev/null" EXIT
fi

sleep 1

LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [[ -z "$LAN_IP" ]]; then
  LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "unknown")
fi

echo ""
echo "Groundcheck backend running:"
echo "  Data API:   http://localhost:8765/api/data"
echo "              http://$LAN_IP:8765/api/data"
echo "  Live feed:  ws://localhost:8766"
echo "              ws://$LAN_IP:8766"

if [[ "$USE_LOGS" =~ ^[Yy] ]]; then
  echo ""
  echo "Logs: serve.log, ws_proxy.log, update.log"
fi

if [[ ! "$USE_NOHUP" =~ ^[Yy] ]]; then
  echo ""
  echo "Running in foreground — press Ctrl+C to stop."
  wait
fi
