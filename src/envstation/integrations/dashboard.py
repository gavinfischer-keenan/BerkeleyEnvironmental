"""Berkeley Dashboard integration — HTTP POST sensor data and alerts."""
from __future__ import annotations

import httpx
import structlog

from envstation import __version__
from envstation.ingest.schema import StationReading

log = structlog.get_logger(__name__)


class DashboardClient:
    def __init__(self, url: str) -> None:
        self.url = url

    async def send_reading(self, reading: StationReading) -> None:
        payload = {
            "data": {
                "weather": reading.weather.model_dump() if reading.weather else None,
                "wind": reading.wind.model_dump() if reading.wind else None,
                "air": reading.air.model_dump() if reading.air else None,
                "soil": [s.model_dump() for s in reading.soil],
                "rain": reading.rain.model_dump() if reading.rain else None,
                "station_id": reading.station_id,
                "timestamp": reading.timestamp.isoformat(),
            },
            "metadata": {"source": "envstation", "version": __version__},
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(self.url, json=payload)
                resp.raise_for_status()
        except Exception:
            log.warning("dashboard.send_failed", url=self.url)

    async def send_alert(self, alert) -> None:
        payload = {
            "data": {
                "alert_type": alert.alert_type, "severity": alert.severity,
                "title": alert.title, "message": alert.message,
                "data": alert.data, "timestamp": alert.timestamp.isoformat(),
            },
            "metadata": {"source": "envstation", "version": __version__},
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(self.url.replace("/ingest/", "/events/"), json=payload)
                resp.raise_for_status()
        except Exception:
            log.warning("dashboard.alert_send_failed")
