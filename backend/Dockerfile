FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir websockets

ENV GROUNDCHECK_HTTP_PORT=8765
ENV GROUNDCHECK_WS_PORT=8766
ENV GROUNDCHECK_MAX_ALT_M=980

EXPOSE 8765 8766

# Bootstrap data.json if missing, then run both servers. Radiosonde updates
# are handled by an external cron/scheduler hitting update.py, same as the
# non-Docker self-host setup (start.sh) — not duplicated here to keep the
# image a single simple process pair.
CMD sh -c '[ -f data.json ] || python3 update.py --days 5; python3 ws_proxy.py & python3 serve.py'
