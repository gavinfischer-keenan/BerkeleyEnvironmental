"""Diablo wind detection — critical for Berkeley Hills fire weather."""
from __future__ import annotations

from collections import deque

import structlog

from envstation.config import Config
from envstation.ingest.schema import WeatherReading, WindReading

log = structlog.get_logger(__name__)

_wind_history: deque[float] = deque(maxlen=120)
DIABLO_BEARING_MIN = 30
DIABLO_BEARING_MAX = 90


def wind_is_offshore(direction_deg: float) -> bool:
    return DIABLO_BEARING_MIN <= direction_deg <= DIABLO_BEARING_MAX


def _sustained_speed() -> float:
    return sum(_wind_history) / len(_wind_history) if _wind_history else 0.0


def evaluate_wind(wind: WindReading, weather: WeatherReading | None, config: Config) -> list:
    from envstation.rules.engine import Alert

    _wind_history.append(wind.speed_mph)
    sustained = _sustained_speed()
    offshore = wind_is_offshore(wind.direction_deg)
    humidity = weather.humidity if weather else 50.0
    alerts: list[Alert] = []

    if not offshore:
        return alerts

    if sustained >= config.diablo_speed_threshold and humidity <= config.diablo_humidity_threshold:
        alerts.append(Alert(
            alert_type="diablo_wind_critical", severity="critical",
            title="🔥 DIABLO WIND EVENT",
            message=f"Critical fire weather: sustained {sustained:.0f} mph offshore, {humidity:.0f}% humidity.",
            data={"sustained_mph": round(sustained, 1), "gust_mph": wind.gust_mph,
                  "direction_deg": wind.direction_deg, "humidity": humidity}))
    elif sustained >= config.diablo_speed_threshold or humidity <= config.diablo_humidity_threshold + 5:
        alerts.append(Alert(
            alert_type="diablo_wind_warning", severity="warning",
            title="⚠️ Elevated Offshore Winds",
            message=f"Offshore winds {sustained:.0f} mph, humidity {humidity:.0f}%.",
            data={"sustained_mph": round(sustained, 1), "direction_deg": wind.direction_deg}))
    elif sustained >= 15:
        alerts.append(Alert(
            alert_type="offshore_wind_info", severity="info",
            title="ℹ️ Offshore Wind Detected",
            message=f"Moderate offshore winds: {sustained:.0f} mph from {wind.direction_deg:.0f}°.",
            data={"sustained_mph": round(sustained, 1), "direction_deg": wind.direction_deg}))
    return alerts
