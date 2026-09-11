FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir websockets

ENV GROUNDCHECK_HTTP_PORT=8765
ENV GROUNDCHECK_WS_PORT=8766
ENV GROUNDCHECK_MAX_ALT_M=980
ENV GROUNDCHECK_BACKFILL_DAYS=5

EXPOSE 8765 8766

# Bootstrap data.json if missing, then run both servers. Radiosonde updates
# are handled by an external cron/scheduler hitting update.py, same as the
# non-Docker self-host setup (start.sh) — not duplicated here to keep the
# image a single simple process pair.
#
# GROUNDCHECK_BACKFILL_DAYS controls how much history the initial fetch
# covers — pass it fresh each run, e.g.:
#   docker run -e GROUNDCHECK_BACKFILL_DAYS=30 ...
# Only applies when data.json doesn't already exist (a mounted volume with
# existing data is never re-backfilled).
CMD sh -c '[ -f data.json ] || python3 update.py --days "$GROUNDCHECK_BACKFILL_DAYS"; python3 ws_proxy.py & python3 serve.py'
