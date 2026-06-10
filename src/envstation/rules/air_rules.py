"""PM2.5 / AQI alert rules — wildfire smoke detection."""
from __future__ import annotations

from collections import deque

import structlog

from envstation.config import Config
from envstation.ingest.schema import AirQualityReading

log = structlog.get_logger(__name__)

_pm25_history: deque[float] = deque(maxlen=60)

_AQI_COLORS = {
    "Good": "#00e400", "Moderate": "#ffff00",
    "Unhealthy for Sensitive Groups": "#ff7e00", "Unhealthy": "#ff0000",
    "Very Unhealthy": "#8f3f97", "Hazardous": "#7e0023",
}


def get_aqi_color(aqi: int) -> str:
    if aqi <= 50: return _AQI_COLORS["Good"]
    if aqi <= 100: return _AQI_COLORS["Moderate"]
    if aqi <= 150: return _AQI_COLORS["Unhealthy for Sensitive Groups"]
    if aqi <= 200: return _AQI_COLORS["Unhealthy"]
    if aqi <= 300: return _AQI_COLORS["Very Unhealthy"]
    return _AQI_COLORS["Hazardous"]


def _pm25_rate_of_change() -> float:
    if len(_pm25_history) < 10:
        return 0.0
    recent = list(_pm25_history)[-10:]
    older = list(_pm25_history)[:10]
    return (sum(recent) / len(recent)) - (sum(older) / len(older))


def evaluate_air(air: AirQualityReading, config: Config) -> list:
    from envstation.rules.engine import Alert

    _pm25_history.append(air.pm25)
    alerts: list[Alert] = []
    aqi = air.aqi
    roc = _pm25_rate_of_change()

    if roc > 20 and aqi > 50:
        alerts.append(Alert(
            alert_type="smoke_rapid_increase", severity="warning",
            title="🔥 Rapid PM2.5 Increase",
            message=f"PM2.5 rising rapidly (+{roc:.1f}). AQI: {aqi} ({air.aqi_category}).",
            data={"pm25": air.pm25, "aqi": aqi, "rate_of_change": round(roc, 1)}))

    if aqi >= 300:
        alerts.append(Alert(
            alert_type="aqi_hazardous", severity="critical",
            title="☠️ HAZARDOUS AIR QUALITY",
            message=f"AQI {aqi} — HAZARDOUS. PM2.5: {air.pm25:.1f} µg/m³.",
            data={"pm25": air.pm25, "aqi": aqi, "color": get_aqi_color(aqi)}))
    elif aqi >= config.aqi_critical_threshold:
        alerts.append(Alert(
            alert_type="aqi_critical", severity="critical",
            title="🟣 Very Unhealthy Air Quality",
            message=f"AQI {aqi}. PM2.5: {air.pm25:.1f} µg/m³. HVAC filtration recommended.",
            data={"pm25": air.pm25, "aqi": aqi, "color": get_aqi_color(aqi)}))
    elif aqi >= 150:
        alerts.append(Alert(
            alert_type="aqi_unhealthy", severity="warning",
            title="🔴 Unhealthy Air Quality",
            message=f"AQI {aqi}. PM2.5: {air.pm25:.1f} µg/m³.",
            data={"pm25": air.pm25, "aqi": aqi, "color": get_aqi_color(aqi)}))
    elif aqi >= config.aqi_alert_threshold:
        alerts.append(Alert(
            alert_type="aqi_sensitive", severity="info",
            title="🟠 Moderate Air Quality",
            message=f"AQI {aqi} — Unhealthy for Sensitive Groups.",
            data={"pm25": air.pm25, "aqi": aqi, "color": get_aqi_color(aqi)}))
    return alerts
