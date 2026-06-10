"""Health monitoring — tracks station, MQTT, InfluxDB, Rachio connectivity."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog

from envstation.storage.client import health_check as influx_health_check

log = structlog.get_logger(__name__)


class HealthMonitor:
    def __init__(self) -> None:
        self.station_last_seen: datetime | None = None
        self.mqtt_connected: bool = False
        self.influxdb_healthy: bool = False
        self.rachio_connected: bool = False
        self.started_at: datetime = datetime.now(timezone.utc)

    def update_station_seen(self) -> None:
        self.station_last_seen = datetime.now(timezone.utc)

    def check_station_timeout(self, timeout_sec: int = 300) -> bool:
        if self.station_last_seen is None:
            return True
        return (datetime.now(timezone.utc) - self.station_last_seen).total_seconds() > timeout_sec

    def get_status(self) -> dict:
        return {
            "station_last_seen": self.station_last_seen.isoformat() if self.station_last_seen else None,
            "station_timeout": self.check_station_timeout(),
            "mqtt_connected": self.mqtt_connected,
            "influxdb_healthy": self.influxdb_healthy,
            "rachio_connected": self.rachio_connected,
            "uptime_seconds": (datetime.now(timezone.utc) - self.started_at).total_seconds(),
        }

    async def heartbeat_loop(self, interval_sec: int, mqtt_publisher=None, dashboard_client=None) -> None:
        while True:
            try:
                self.influxdb_healthy = influx_health_check()
                status = self.get_status()
                if mqtt_publisher:
                    mqtt_publisher._publish("home/status/environmental-station",
                                           {"status": "online", **status}, qos=0, retain=True)
                if self.check_station_timeout():
                    log.warning("health.station_timeout", last_seen=str(self.station_last_seen))
                log.debug("health.heartbeat", **status)
            except Exception:
                log.exception("health.heartbeat_error")
            await asyncio.sleep(interval_sec)
