"""Composite fire weather rule — combines wind, humidity, soil, rain."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import structlog

from envstation.config import Config
from envstation.ingest.schema import RainReading, SoilReading, WeatherReading, WindReading
from envstation.rules.wind_rules import wind_is_offshore

log = structlog.get_logger(__name__)

_last_rain_time: datetime | None = None


def evaluate_fire_weather(
    wind: WindReading | None, weather: WeatherReading | None,
    soil_readings: list[SoilReading], rain: RainReading | None, config: Config,
) -> tuple[list, object | None]:
    from envstation.rules.engine import Alert, PreHydrationCommand

    global _last_rain_time
    alerts: list[Alert] = []
    prehydration = None

    if rain and rain.rate_mm_hr > 0.5:
        _last_rain_time = datetime.now(timezone.utc)

    if not wind or not weather:
        return alerts, prehydration

    offshore = wind_is_offshore(wind.direction_deg)
    high_wind = wind.speed_mph >= config.diablo_speed_threshold
    low_humidity = weather.humidity <= config.diablo_humidity_threshold
    avg_soil = (sum(s.moisture_pct for s in soil_readings) / len(soil_readings)) if soil_readings else 50.0
    dry_soil = avg_soil < 30.0
    no_recent_rain = (_last_rain_time is None or
                      (datetime.now(timezone.utc) - _last_rain_time) > timedelta(hours=48))

    conditions_met = sum([offshore, high_wind, low_humidity, dry_soil, no_recent_rain])

    if conditions_met >= 4 and offshore and high_wind:
        zone_names = [s.zone for s in soil_readings] if soil_readings else ["all"]
        prehydration = PreHydrationCommand(
            zones=zone_names, duration_per_zone_sec=900,
            reason=f"Fire weather: {wind.speed_mph:.0f} mph offshore, {weather.humidity:.0f}% humidity, soil {avg_soil:.0f}%")
        alerts.append(Alert(
            alert_type="fire_weather_critical", severity="critical",
            title="🔥 CRITICAL FIRE WEATHER — PRE-HYDRATION INITIATED",
            message=(f"Wind: {wind.speed_mph:.0f} mph offshore | Humidity: {weather.humidity:.0f}% | "
                     f"Soil: {avg_soil:.0f}% | No rain 48h+. Pre-hydrating {len(zone_names)} zones."),
            data={"wind_speed": wind.speed_mph, "humidity": weather.humidity,
                  "soil_avg": round(avg_soil, 1), "zones": zone_names, "conditions_met": conditions_met}))

    return alerts, prehydration
