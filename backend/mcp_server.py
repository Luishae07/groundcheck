#!/usr/bin/env python3
"""Groundcheck MCP server — stdio JSON-RPC, no external deps."""
import json
import sys
import math
import os
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.environ.get("GROUNDCHECK_DATA_PATH", os.path.join(BASE, "data.json"))
PREDICTOR_URL = os.environ.get("GROUNDCHECK_PREDICTOR_URL", "http://localhost:8768/predict")

def load_points():
    with open(DATA_PATH) as f:
        d = json.load(f)
    return d.get("features", d) if isinstance(d, dict) else d

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

def tool_current_reading(args):
    points = load_points()
    if not points:
        return {"error": "no data available"}
    latest = max(points, key=lambda p: p.get("tsunix", 0))
    return latest

def tool_nearest_station(args):
    import time
    lat = args.get("lat")
    lon = args.get("lon")
    if lat is None or lon is None:
        return {"error": "lat and lon required"}
    max_age_days = args.get("max_age_days")
    points = load_points()
    if not points:
        return {"error": "no data available"}
    if max_age_days is not None:
        cutoff = time.time() - max_age_days * 86400
        points = [p for p in points if p.get("tsunix", 0) >= cutoff]
        if not points:
            return {"error": f"no readings within the last {max_age_days} day(s)"}
    best = min(points, key=lambda p: haversine_km(lat, lon, p["lat"], p["lon"]))
    dist = haversine_km(lat, lon, best["lat"], best["lon"])
    out = dict(best)
    out["distance_km"] = round(dist, 2)
    return out

def tool_station_history(args):
    station_id = args.get("id")
    if not station_id:
        return {"error": "id required"}
    limit = int(args.get("limit", 20))
    points = load_points()
    matches = [p for p in points if p.get("id") == station_id]
    matches.sort(key=lambda p: p.get("tsunix", 0), reverse=True)
    return {"id": station_id, "count": len(matches), "readings": matches[:limit]}

def tool_search_readings(args):
    min_temp = args.get("min_temp")
    max_temp = args.get("max_temp")
    limit = int(args.get("limit", 20))
    points = load_points()
    filtered = points
    if min_temp is not None:
        filtered = [p for p in filtered if p.get("temp") is not None and p["temp"] >= min_temp]
    if max_temp is not None:
        filtered = [p for p in filtered if p.get("temp") is not None and p["temp"] <= max_temp]
    filtered.sort(key=lambda p: p.get("tsunix", 0), reverse=True)
    return {"count": len(filtered), "readings": filtered[:limit]}

def tool_predictor(args):
    try:
        with urllib.request.urlopen(PREDICTOR_URL, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def tool_stats(args):
    points = load_points()
    if not points:
        return {"error": "no data available"}
    temps = [p["temp"] for p in points if p.get("temp") is not None]
    return {
        "total_readings": len(points),
        "min_temp": min(temps) if temps else None,
        "max_temp": max(temps) if temps else None,
        "avg_temp": round(sum(temps) / len(temps), 2) if temps else None,
        "unique_stations": len({p["id"] for p in points if p.get("id")}),
    }

TOOLS = {
    "current_reading": {
        "description": "Get the most recent ground-level radiosonde reading in the entire dataset.",
        "inputSchema": {"type": "object", "properties": {}},
        "fn": tool_current_reading,
    },
    "nearest_station": {
        "description": "Find the nearest ground-level radiosonde reading to a given lat/lon, optionally restricted to readings no older than max_age_days (e.g. 1 for today, 7 for last week).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "max_age_days": {"type": "number", "description": "Only consider readings within this many days old"},
            },
            "required": ["lat", "lon"],
        },
        "fn": tool_nearest_station,
    },
    "station_history": {
        "description": "Get historical readings for a specific station ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["id"],
        },
        "fn": tool_station_history,
    },
    "search_readings": {
        "description": "Search ground-level readings by temperature range, most recent first.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "min_temp": {"type": "number"},
                "max_temp": {"type": "number"},
                "limit": {"type": "integer", "default": 20},
            },
        },
        "fn": tool_search_readings,
    },
    "predictor": {
        "description": "Get the app's own diurnal-pattern-based next-hours prediction (not an external forecast API).",
        "inputSchema": {"type": "object", "properties": {}},
        "fn": tool_predictor,
    },
    "stats": {
        "description": "Get summary statistics of the current ground-level dataset (count, min/max/avg temp, unique stations).",
        "inputSchema": {"type": "object", "properties": {}},
        "fn": tool_stats,
    },
}

def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

def handle(req):
    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "groundcheck-mcp", "version": "1.0.0"},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        tools_list = [
            {"name": name, "description": t["description"], "inputSchema": t["inputSchema"]}
            for name, t in TOOLS.items()
        ]
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_list}}

    if method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {}) or {}
        tool = TOOLS.get(name)
        if not tool:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"unknown tool: {name}"}}
        try:
            result = tool["fn"](args)
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
        }

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"unknown method: {method}"}}

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(req)
        if resp is not None:
            send(resp)

if __name__ == "__main__":
    main()
