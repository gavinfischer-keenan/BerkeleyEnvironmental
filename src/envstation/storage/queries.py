"""Pre-built Flux queries for environmental sensor data."""
from __future__ import annotations

from typing import Any

import structlog

from envstation.config import get_config
from envstation.storage.client import get_influx_client

log = structlog.get_logger(__name__)


def _run_query(flux: str) -> list[dict[str, Any]]:
    cfg = get_config()
    client = get_influx_client()
    tables = client.query_api().query(flux, org=cfg.influxdb_org)
    results: list[dict[str, Any]] = []
    for table in tables:
        for record in table.records:
            results.append({
                "time": str(record.get_time()),
                "measurement": record.get_measurement(),
                "field": record.get_field(),
                "value": record.get_value(),
                **{k: v for k, v in record.values.items()
                   if k not in ("_time", "_measurement", "_field", "_value", "result", "table")},
            })
    return results


def get_latest(measurement: str, station: str = "berkeley-hilltop") -> list[dict]:
    cfg = get_config()
    return _run_query(f'''from(bucket: "{cfg.influxdb_bucket_raw}")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
  |> filter(fn: (r) => r["station"] == "{station}")
  |> last()''')


def get_history(measurement: str, field: str, station: str = "berkeley-hilltop",
                start: str = "-1h", stop: str = "now()") -> list[dict]:
    cfg = get_config()
    return _run_query(f'''from(bucket: "{cfg.influxdb_bucket_raw}")
  |> range(start: {start}, stop: {stop})
  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
  |> filter(fn: (r) => r["_field"] == "{field}")
  |> filter(fn: (r) => r["station"] == "{station}")''')


def get_daily_summary(station: str = "berkeley-hilltop", date: str = "today()") -> list[dict]:
    cfg = get_config()
    start = f"{date}T00:00:00Z" if date != "today()" else "-24h"
    return _run_query(f'''from(bucket: "{cfg.influxdb_bucket_raw}")
  |> range(start: {start})
  |> filter(fn: (r) => r["station"] == "{station}")
  |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)''')


def get_soil_by_zone(zone: str, station: str = "berkeley-hilltop", hours: int = 24) -> list[dict]:
    cfg = get_config()
    return _run_query(f'''from(bucket: "{cfg.influxdb_bucket_raw}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r["_measurement"] == "soil")
  |> filter(fn: (r) => r["station"] == "{station}")
  |> filter(fn: (r) => r["zone"] == "{zone}")
  |> filter(fn: (r) => r["_field"] == "moisture_pct")''')


def get_wind_rose(station: str = "berkeley-hilltop", hours: int = 24) -> list[dict]:
    cfg = get_config()
    return _run_query(f'''from(bucket: "{cfg.influxdb_bucket_raw}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r["_measurement"] == "wind")
  |> filter(fn: (r) => r["station"] == "{station}")''')


def get_rain_accumulation(station: str = "berkeley-hilltop", hours: int = 24) -> float:
    cfg = get_config()
    results = _run_query(f'''from(bucket: "{cfg.influxdb_bucket_raw}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r["_measurement"] == "rain")
  |> filter(fn: (r) => r["_field"] == "accumulation_mm")
  |> filter(fn: (r) => r["station"] == "{station}")
  |> last()''')
    return float(results[-1].get("value", 0.0)) if results else 0.0
