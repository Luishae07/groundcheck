#!/usr/bin/env bash
# Groundcheck backend launcher — serve.py (HTTP data API) + ws_proxy.py (live feed).
set -e
cd "$(dirname "$0")"

echo "Groundcheck backend"
echo "===================="

# --- ports ---
read -rp "HTTP data API port [8765]: " HTTP_PORT
HTTP_PORT="${HTTP_PORT:-8765}"
read -rp "WebSocket live-feed port [8766]: " WS_PORT
WS_PORT="${WS_PORT:-8766}"
export GROUNDCHECK_HTTP_PORT="$HTTP_PORT"
export GROUNDCHECK_WS_PORT="$WS_PORT"

# --- ground-level altitude filter ---
read -rp "Max ground-level altitude filter in meters [980]: " MAX_ALT
MAX_ALT="${MAX_ALT:-980}"
export GROUNDCHECK_MAX_ALT_M="$MAX_ALT"

# --- data.json bootstrap ---
if [[ ! -f "data.json" ]]; then
  read -rp "data.json not found. Create it now? (y/n): " CREATE_DATA
  if [[ "$CREATE_DATA" =~ ^[Yy] ]]; then
    sleep 2
    echo "How many days of history should the initial fetch cover?"
    select DAYS in 1 3 5 9 10 20 50 200 500 600 800; do
      if [[ -n "$DAYS" ]]; then
        break
      fi
    done
    echo "Fetching last $DAYS day(s) of radiosonde history — this can take a while for large ranges..."
    python3 update.py --days "$DAYS"
    echo "data.json created."
  fi
fi

# --- cron setup ---
read -rp "Set up automatic radiosonde checks via cron? (y/n): " USE_CRON
if [[ "$USE_CRON" =~ ^[Yy] ]]; then
  read -rp "Check every minute? (y/n): " CRON_MINUTE
  read -rp "Also check once daily (deeper 24h window, catches anything missed)? (y/n): " CRON_DAILY
  if [[ ! "$CRON_MINUTE" =~ ^[Yy] ]] && [[ ! "$CRON_DAILY" =~ ^[Yy] ]]; then
    read -rp "Neither selected — check every N minutes instead (0 to skip cron entirely): " CRON_CUSTOM_MIN
  fi
fi

read -rp "Run in background with nohup? (y/n): " USE_NOHUP
read -rp "Enable logs? (y/n): " USE_LOGS
read -rp "Open the app in your browser once it's running? (y/n): " OPEN_BROWSER

if [[ "$USE_LOGS" =~ ^[Yy] ]]; then
  SERVE_OUT="serve.log"
  WS_OUT="ws_proxy.log"
  UPDATE_OUT="update.log"
else
  SERVE_OUT="/dev/null"
  WS_OUT="/dev/null"
  UPDATE_OUT="/dev/null"
fi

# --- install cron jobs per the choices above ---
if [[ "$USE_CRON" =~ ^[Yy] ]]; then
  SCRIPT_DIR="$(pwd)"
  if [[ "$UPDATE_OUT" == "/dev/null" ]]; then
    UPDATE_LOG_TARGET="/dev/null"
  else
    UPDATE_LOG_TARGET="$SCRIPT_DIR/$UPDATE_OUT"
  fi
  CRON_MARKER="# groundcheck-backend-auto"
  NEW_CRON_LINES=""

  if [[ "$CRON_MINUTE" =~ ^[Yy] ]]; then
    NEW_CRON_LINES+="* * * * * cd $SCRIPT_DIR && GROUNDCHECK_MAX_ALT_M=$MAX_ALT python3 update.py --window 60 >> $UPDATE_LOG_TARGET 2>&1 $CRON_MARKER"$'\n'
  fi
  if [[ "$CRON_DAILY" =~ ^[Yy] ]]; then
    NEW_CRON_LINES+="0 3 * * * cd $SCRIPT_DIR && GROUNDCHECK_MAX_ALT_M=$MAX_ALT python3 update.py --window 86400 >> $UPDATE_LOG_TARGET 2>&1 $CRON_MARKER"$'\n'
  fi
  if [[ -n "$CRON_CUSTOM_MIN" ]] && [[ "$CRON_CUSTOM_MIN" != "0" ]]; then
    NEW_CRON_LINES+="*/$CRON_CUSTOM_MIN * * * * cd $SCRIPT_DIR && GROUNDCHECK_MAX_ALT_M=$MAX_ALT python3 update.py --window $((CRON_CUSTOM_MIN * 60)) >> $UPDATE_LOG_TARGET 2>&1 $CRON_MARKER"$'\n'
  fi

  if [[ -n "$NEW_CRON_LINES" ]] && command -v crontab >/dev/null 2>&1; then
    ( crontab -l 2>/dev/null | grep -v "$CRON_MARKER" ; printf '%s' "$NEW_CRON_LINES" ) | crontab -
    echo "Installed cron jobs."
  elif [[ -z "$NEW_CRON_LINES" ]]; then
    echo "No cron cadence selected — skipping."
  else
    echo "crontab not available — skipping automatic radiosonde checks."
  fi
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
echo "  Data API:   http://localhost:$HTTP_PORT/api/data"
echo "              http://$LAN_IP:$HTTP_PORT/api/data"
echo "  Live feed:  ws://localhost:$WS_PORT"
echo "              ws://$LAN_IP:$WS_PORT"
echo "  Altitude filter: <= ${MAX_ALT}m"

if [[ "$USE_LOGS" =~ ^[Yy] ]]; then
  echo ""
  echo "Logs: serve.log, ws_proxy.log, update.log"
fi

if [[ "$OPEN_BROWSER" =~ ^[Yy] ]]; then
  URL="http://localhost:$HTTP_PORT/"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
  elif command -v open >/dev/null 2>&1; then
    open "$URL"
  else
    echo "Could not detect a way to open a browser automatically — open $URL manually."
  fi
fi

if [[ ! "$USE_NOHUP" =~ ^[Yy] ]]; then
  echo ""
  echo "Running in foreground — press Ctrl+C to stop."
  wait
fi
