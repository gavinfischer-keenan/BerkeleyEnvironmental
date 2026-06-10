"""Rachio smart irrigation REST API client."""
from __future__ import annotations

import httpx
import structlog

log = structlog.get_logger(__name__)


class RachioAPIError(Exception):
    """Raised on non-2xx Rachio API response."""


class RachioClient:
    BASE_URL = "https://api.rach.io/1/public"
    DAILY_LIMIT = 3500

    def __init__(self, api_key: str, device_id: str | None = None) -> None:
        self.api_key = api_key
        self.device_id = device_id
        self.requests_today: int = 0
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def _request(self, method: str, path: str, json: dict | None = None) -> dict:
        self.requests_today += 1
        if self.requests_today > self.DAILY_LIMIT:
            log.warning("rachio.rate_limit_approaching", count=self.requests_today)
        url = f"{self.BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.request(method, url, headers=self._headers, json=json)
            if resp.status_code >= 400:
                log.error("rachio.api_error", status=resp.status_code, path=path)
                raise RachioAPIError(f"{resp.status_code}: {resp.text[:200]}")
            return resp.json() if resp.content else {}

    async def get_person(self) -> dict:
        return await self._request("GET", "/person/info")

    async def get_device(self, device_id: str | None = None) -> dict:
        did = device_id or self.device_id
        if not did: raise ValueError("No device_id provided")
        return await self._request("GET", f"/device/{did}")

    async def get_zones(self, device_id: str | None = None) -> list[dict]:
        device = await self.get_device(device_id)
        return device.get("zones", [])

    async def start_zone(self, zone_id: str, duration_sec: int) -> None:
        await self._request("PUT", "/zone/start", json={"id": zone_id, "duration": duration_sec})
        log.info("rachio.zone_started", zone_id=zone_id, duration_sec=duration_sec)

    async def start_multiple_zones(self, zones: list[dict]) -> None:
        await self._request("PUT", "/zone/start_multiple", json={"zones": zones})
        log.info("rachio.zones_started", count=len(zones))

    async def stop_all(self) -> None:
        if not self.device_id: raise ValueError("No device_id")
        await self._request("PUT", "/device/stop_water", json={"id": self.device_id})
        log.info("rachio.all_stopped")

    async def set_rain_delay(self, duration_sec: int) -> None:
        if not self.device_id: raise ValueError("No device_id")
        await self._request("PUT", "/device/rain_delay", json={"id": self.device_id, "duration": duration_sec})

    async def device_standby(self, duration_sec: int) -> None:
        if not self.device_id: raise ValueError("No device_id")
        await self._request("PUT", "/device/off", json={"id": self.device_id, "duration": duration_sec})

    async def device_resume(self) -> None:
        if not self.device_id: raise ValueError("No device_id")
        await self._request("PUT", "/device/on", json={"id": self.device_id})
