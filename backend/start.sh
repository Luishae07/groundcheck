#!/usr/bin/env bash
# Groundcheck backend launcher — serve.py (HTTP data API) + ws_proxy.py (live feed).
set -e
cd "$(dirname "$0")"

echo "Groundcheck backend"
echo "===================="
read -rp "Run in background with nohup? (y/n): " USE_NOHUP
read -rp "Enable logs? (y/n): " USE_LOGS

if [[ "$USE_LOGS" =~ ^[Yy] ]]; then
  SERVE_OUT="serve.log"
  WS_OUT="ws_proxy.log"
else
  SERVE_OUT="/dev/null"
  WS_OUT="/dev/null"
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
  echo "Logs: serve.log, ws_proxy.log"
fi

if [[ ! "$USE_NOHUP" =~ ^[Yy] ]]; then
  echo ""
  echo "Running in foreground — press Ctrl+C to stop."
  wait
fi
