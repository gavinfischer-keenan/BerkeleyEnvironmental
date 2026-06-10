"""Heavy rain / atmospheric river detection."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone

import structlog

from envstation.config import Config
from envstation.ingest.schema import RainReading

log = structlog.get_logger(__name__)

_rain_history: deque[tuple[datetime, float]] = deque(maxlen=1440)


def _accumulation_24h() -> float:
    now = datetime.now(timezone.utc)
    total = 0.0
    for ts, acc in _rain_history:
        if (now - ts).total_seconds() <= 86400:
            total = max(total, acc)
    return total


def evaluate_rain(rain: RainReading, config: Config) -> list:
    from envstation.rules.engine import Alert

    _rain_history.append((datetime.now(timezone.utc), rain.accumulation_mm))
    alerts: list[Alert] = []
    rate = rain.rate_mm_hr
    acc_24h = _accumulation_24h()

    if rate >= config.rain_extreme_rate:
        alerts.append(Alert(
            alert_type="rain_extreme", severity="critical",
            title="🌊 ATMOSPHERIC RIVER",
            message=f"Extreme rainfall: {rate:.1f} mm/hr. 24h: {acc_24h:.1f} mm.",
            data={"rate_mm_hr": rate, "accumulation_24h_mm": round(acc_24h, 1)}))
    elif rate >= config.rain_heavy_rate:
        alerts.append(Alert(
            alert_type="rain_heavy", severity="warning",
            title="🌧️ Heavy Rain Alert",
            message=f"Heavy rainfall: {rate:.1f} mm/hr. 24h: {acc_24h:.1f} mm.",
            data={"rate_mm_hr": rate, "accumulation_24h_mm": round(acc_24h, 1)}))

    if acc_24h >= 50 and rate < config.rain_heavy_rate:
        alerts.append(Alert(
            alert_type="rain_24h_sustained", severity="warning",
            title="💧 Sustained Heavy Rain",
            message=f"24h accumulation: {acc_24h:.1f} mm. Monitor drainage.",
            data={"accumulation_24h_mm": round(acc_24h, 1)}))
    return alerts
