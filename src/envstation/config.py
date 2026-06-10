"""Pydantic-settings configuration — all env vars with typed defaults."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Config(BaseSettings):
    """Application configuration loaded from environment / .env file."""

    model_config = {"env_file": str(_ENV_FILE) if _ENV_FILE.exists() else None, "extra": "ignore"}

    # ── MQTT ──────────────────────────────────────────────────────
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic_prefix: str = "home/sensors"

    # ── InfluxDB ──────────────────────────────────────────────────
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = ""
    influxdb_org: str = "home"
    influxdb_bucket_raw: str = "sensors-raw"
    influxdb_bucket_hourly: str = "sensors-hourly"
    influxdb_bucket_daily: str = "sensors-daily"

    # ── Rachio ────────────────────────────────────────────────────
    rachio_api_key: str = ""
    rachio_device_id: str = ""
    zone_mapping: dict[str, str] = {}

    # ── Dashboard ─────────────────────────────────────────────────
    dashboard_url: str = "http://localhost:5050/api/ingest/environmental-station"

    # ── Station ───────────────────────────────────────────────────
    station_id: str = "berkeley-hilltop"
    station_lat: float = 37.8696
    station_lon: float = -122.2491
    station_elevation: float = 161.1

    # ── Alert Thresholds ──────────────────────────────────────────
    diablo_speed_threshold: float = 25.0
    diablo_humidity_threshold: float = 20.0
    aqi_alert_threshold: int = 100
    aqi_critical_threshold: int = 200
    soil_dry_threshold: float = 25.0
    soil_wet_threshold: float = 85.0
    soil_critical_threshold: float = 95.0
    rain_heavy_rate: float = 10.0
    rain_extreme_rate: float = 25.0
    alert_cooldown_sec: int = 300

    # ── Telemetry ─────────────────────────────────────────────────
    heartbeat_interval_sec: int = 60
    station_timeout_sec: int = 300

    # ── API ────────────────────────────────────────────────────────
    api_port: int = 8090

    # ── Logging ───────────────────────────────────────────────────
    log_level: str = "INFO"

    @field_validator("zone_mapping", mode="before")
    @classmethod
    def _parse_zone_mapping(cls, v: Any) -> dict[str, str]:
        if isinstance(v, str):
            return json.loads(v) if v.strip() else {}
        return v  # type: ignore[return-value]


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Return the singleton Config instance."""
    return Config()
