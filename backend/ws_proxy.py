#!/usr/bin/env python3
"""
Fan-out proxy for zeesen.mine.nu's live radiosonde WebSocket feed.

Connects once upstream (wss://zeesen.mine.nu:7890), subscribes to all live
sonde updates, and re-broadcasts every message to however many local
clients are connected. Local clients connect to ws://localhost:8766 —
that gets exposed to the internet via our own Cloudflare tunnel, so the
app never talks to zeesen directly.
"""
import asyncio
import json
import os
import websockets

UPSTREAM_URL = "wss://zeesen.mine.nu:7890"
LOCAL_PORT = int(os.environ.get("GROUNDCHECK_WS_PORT", 8766))

clients = set()
latest_sonde = {"data": None}  # last known live sonde message, for late-joining clients

def log(msg):
    print(f"[ws_proxy] {msg}", flush=True)

async def upstream_loop():
    while True:
        try:
            async with websockets.connect(UPSTREAM_URL, open_timeout=15) as ws:
                log("connected upstream")
                await ws.send(json.dumps({"user": 1, "places": 1, "geojson": 1}))
                async for message in ws:
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        continue
                    # Only forward actual live sonde telemetry (has real features
                    # with a "properties.temp" key), skip the station/place lists.
                    feats = data.get("features") or []
                    if feats and "temp" in feats[0].get("properties", {}):
                        latest_sonde["data"] = message
                        dead = set()
                        for client in clients:
                            try:
                                await client.send(message)
                            except Exception:
                                dead.add(client)
                        clients.difference_update(dead)
        except Exception as e:
            log(f"upstream error: {e}, retrying in 5s")
            await asyncio.sleep(5)

async def handle_client(websocket):
    clients.add(websocket)
    log(f"client connected ({len(clients)} total)")
    try:
        if latest_sonde["data"]:
            await websocket.send(latest_sonde["data"])
        async for _ in websocket:
            pass  # ignore anything clients send
    finally:
        clients.discard(websocket)
        log(f"client disconnected ({len(clients)} total)")

async def main():
    async with websockets.serve(handle_client, "0.0.0.0", LOCAL_PORT):
        log(f"listening on :{LOCAL_PORT}")
        await upstream_loop()

if __name__ == "__main__":
    asyncio.run(main())
