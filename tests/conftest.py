"""Shared test fixtures for the environmental station."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from envstation.config import Config
from envstation.ingest.schema import (
    AirQualityReading, RainReading, SoilReading, StationReading,
    WeatherReading, WindReading,
)


@pytest.fixture
def config() -> Config:
    return Config(influxdb_token="test-token", rachio_api_key="test-key")


@pytest.fixture
def sample_station_reading() -> StationReading:
    return StationReading(
        station_id="test-station", timestamp=datetime.now(timezone.utc),
        weather=WeatherReading(temperature=68.0, humidity=55.0, pressure=1013.25),
        wind=WindReading(speed_mph=8.0, direction_deg=270.0, gust_mph=12.0),
        air=AirQualityReading(pm25=8.0, pm10=12.0),
        soil=[SoilReading(zone="zone_front", moisture_pct=35.0),
              SoilReading(zone="zone_hillside", depth="12in", moisture_pct=42.0)],
        rain=RainReading(rate_mm_hr=0.0, accumulation_mm=0.0))


@pytest.fixture
def sample_wind_diablo() -> WindReading:
    return WindReading(speed_mph=32.0, direction_deg=45.0, gust_mph=45.0)


@pytest.fixture
def sample_wind_normal() -> WindReading:
    return WindReading(speed_mph=8.0, direction_deg=270.0, gust_mph=12.0)


@pytest.fixture
def sample_air_smoky() -> AirQualityReading:
    return AirQualityReading(pm25=180.0, pm10=220.0)


@pytest.fixture
def sample_air_clean() -> AirQualityReading:
    return AirQualityReading(pm25=8.0, pm10=12.0)


@pytest.fixture
def sample_soil_dry() -> SoilReading:
    return SoilReading(zone="zone_front", moisture_pct=18.0)


@pytest.fixture
def sample_soil_saturated() -> SoilReading:
    return SoilReading(zone="zone_hillside", depth="12in", moisture_pct=92.0)


@pytest.fixture
def sample_rain_heavy() -> RainReading:
    return RainReading(rate_mm_hr=15.0, accumulation_mm=30.0)
