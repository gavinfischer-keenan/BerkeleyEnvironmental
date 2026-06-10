"""InfluxDB client singleton."""
from __future__ import annotations

import structlog
from influxdb_client import InfluxDBClient

from envstation.config import get_config

log = structlog.get_logger(__name__)

_client: InfluxDBClient | None = None


def get_influx_client() -> InfluxDBClient:
    """Return the singleton InfluxDB client."""
    global _client
    if _client is None:
        cfg = get_config()
        _client = InfluxDBClient(url=cfg.influxdb_url, token=cfg.influxdb_token, org=cfg.influxdb_org)
        log.info("influxdb.client_created", url=cfg.influxdb_url)
    return _client


def health_check() -> bool:
    """Return True if InfluxDB is reachable."""
    try:
        return get_influx_client().ping()
    except Exception:
        log.exception("influxdb.health_check_failed")
        return False
