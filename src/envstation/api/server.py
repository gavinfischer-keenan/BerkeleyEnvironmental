"""FastAPI REST API for querying environmental sensor data."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from envstation import __version__
from envstation.storage import queries
from envstation.storage.client import health_check

app = FastAPI(title="Berkeley Environmental Station API", version=__version__)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_rules_engine = None
_rachio_client = None
_health_monitor = None


def set_dependencies(rules_engine=None, rachio_client=None, health_monitor=None):
    global _rules_engine, _rachio_client, _health_monitor
    _rules_engine = rules_engine
    _rachio_client = rachio_client
    _health_monitor = health_monitor


@app.get("/health")
async def get_health():
    return {"status": "ok", "version": __version__, "influxdb": health_check(),
            "health_monitor": _health_monitor.get_status() if _health_monitor else None}


@app.get("/readings/latest")
async def get_latest_all():
    result = {}
    for m in ["weather", "wind", "air_quality", "soil", "rain"]:
        try:
            result[m] = queries.get_latest(m)
        except Exception:
            result[m] = []
    return result


@app.get("/readings/{measurement}")
async def get_latest_measurement(measurement: str):
    valid = {"weather", "wind", "air_quality", "soil", "rain"}
    if measurement not in valid:
        raise HTTPException(400, f"Invalid measurement. Use: {valid}")
    return queries.get_latest(measurement)


@app.get("/history/{measurement}/{field}")
async def get_history(measurement: str, field: str,
                      start: str = Query("-1h"), stop: str = Query("now()")):
    return queries.get_history(measurement, field, start=start, stop=stop)


@app.get("/history/soil/{zone}")
async def get_soil_history(zone: str, hours: int = Query(24)):
    return queries.get_soil_by_zone(zone, hours=hours)


@app.get("/alerts")
async def get_alerts():
    if not _rules_engine:
        return []
    return [{"alert_id": a.alert_id, "alert_type": a.alert_type, "severity": a.severity,
             "title": a.title, "message": a.message, "data": a.data,
             "timestamp": a.timestamp.isoformat()} for a in _rules_engine.get_active_alerts()]


@app.get("/rachio/status")
async def get_rachio_status():
    if not _rachio_client:
        raise HTTPException(503, "Rachio not configured")
    try:
        device = await _rachio_client.get_device()
        return {"device": device.get("name"), "status": device.get("status"),
                "zones": [{"id": z["id"], "name": z.get("name"), "enabled": z.get("enabled")}
                          for z in device.get("zones", [])],
                "requests_today": _rachio_client.requests_today}
    except Exception as e:
        raise HTTPException(502, str(e))


@app.post("/rachio/zone/{zone_id}/start")
async def start_rachio_zone(zone_id: str, duration: int = Query(300)):
    if not _rachio_client:
        raise HTTPException(503, "Rachio not configured")
    await _rachio_client.start_zone(zone_id, duration)
    return {"status": "started", "zone_id": zone_id, "duration": duration}


@app.post("/rachio/stop")
async def stop_rachio():
    if not _rachio_client:
        raise HTTPException(503, "Rachio not configured")
    await _rachio_client.stop_all()
    return {"status": "stopped"}


@app.get("/summary/daily")
async def get_daily_summary(date: str = Query("today()")):
    return queries.get_daily_summary(date=date)


@app.get("/summary/wind-rose")
async def get_wind_rose(hours: int = Query(24)):
    return queries.get_wind_rose(hours=hours)
