"""Pydantic v2 data models for environmental sensor readings."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from pydantic import BaseModel, Field, computed_field


# ---------------------------------------------------------------------------
# EPA AQI Breakpoint Table for PM2.5 (24-hour)
# ---------------------------------------------------------------------------
_AQI_BREAKPOINTS: list[tuple[float, float, int, int, str]] = [
    (0.0,    12.0,    0,   50,  "Good"),
    (12.1,   35.4,   51,  100,  "Moderate"),
    (35.5,   55.4,  101,  150,  "Unhealthy for Sensitive Groups"),
    (55.5,  150.4,  151,  200,  "Unhealthy"),
    (150.5, 250.4,  201,  300,  "Very Unhealthy"),
    (250.5, 500.4,  301,  500,  "Hazardous"),
]


def compute_aqi(pm25: float) -> tuple[int, str]:
    """Compute EPA AQI and category string from a PM2.5 reading (µg/m³)."""
    if pm25 < 0:
        return 0, "Good"
    for c_lo, c_hi, i_lo, i_hi, cat in _AQI_BREAKPOINTS:
        if c_lo <= pm25 <= c_hi:
            aqi = round((i_hi - i_lo) / (c_hi - c_lo) * (pm25 - c_lo) + i_lo)
            return aqi, cat
    return 500, "Hazardous"


def compute_dew_point(temp_f: float, humidity: float) -> float:
    """Magnus-formula dew point. Accepts °F, returns °F."""
    temp_c = (temp_f - 32) * 5 / 9
    a, b = 17.27, 237.7
    alpha = (a * temp_c) / (b + temp_c) + math.log(max(humidity, 1) / 100)
    dp_c = (b * alpha) / (a - alpha)
    return dp_c * 9 / 5 + 32


class WeatherReading(BaseModel):
    temperature: float = Field(..., description="Temperature in °F")
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity %")
    pressure: float = Field(..., description="Barometric pressure in hPa")

    @computed_field  # type: ignore[misc]
    @property
    def dew_point(self) -> float:
        return round(compute_dew_point(self.temperature, self.humidity), 1)


class WindReading(BaseModel):
    speed_mph: float = Field(..., ge=0)
    direction_deg: float = Field(..., ge=0, lt=360)
    gust_mph: float = Field(0.0, ge=0)


class AirQualityReading(BaseModel):
    pm25: float = Field(..., ge=0, description="PM2.5 µg/m³")
    pm10: float = Field(0.0, ge=0, description="PM10 µg/m³")

    @computed_field  # type: ignore[misc]
    @property
    def aqi(self) -> int:
        val, _ = compute_aqi(self.pm25)
        return val

    @computed_field  # type: ignore[misc]
    @property
    def aqi_category(self) -> str:
        _, cat = compute_aqi(self.pm25)
        return cat


class SoilReading(BaseModel):
    zone: str = Field(..., description="Garden zone name")
    depth: str = Field("6in", description="Probe depth")
    moisture_pct: float = Field(..., ge=0, le=100)
    temp_f: float | None = None


class RainReading(BaseModel):
    rate_mm_hr: float = Field(0.0, ge=0)
    accumulation_mm: float = Field(0.0, ge=0)
    tips_total: int | None = None


class StationReading(BaseModel):
    station_id: str = "berkeley-hilltop"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    firmware: str | None = None
    uptime_s: int | None = None
    weather: WeatherReading | None = None
    wind: WindReading | None = None
    air: AirQualityReading | None = None
    soil: list[SoilReading] = Field(default_factory=list)
    rain: RainReading | None = None
