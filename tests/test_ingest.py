"""Tests for the ingest layer — schema parsing and AQI calculation."""
from __future__ import annotations

from envstation.ingest.schema import StationReading, compute_aqi, compute_dew_point


def test_parse_batch_payload():
    payload = {
        "station_id": "test",
        "weather": {"temperature": 72.0, "humidity": 50.0, "pressure": 1013.0},
        "wind": {"speed_mph": 10.0, "direction_deg": 180.0, "gust_mph": 15.0},
        "air": {"pm25": 25.0, "pm10": 35.0},
        "soil": [{"zone": "front", "moisture_pct": 40.0}],
        "rain": {"rate_mm_hr": 0.0, "accumulation_mm": 0.0},
    }
    reading = StationReading(**payload)
    assert reading.station_id == "test"
    assert reading.weather.temperature == 72.0
    assert reading.wind.speed_mph == 10.0
    assert len(reading.soil) == 1


def test_compute_aqi_good():
    aqi, cat = compute_aqi(8.0)
    assert aqi <= 50
    assert cat == "Good"


def test_compute_aqi_unhealthy():
    aqi, cat = compute_aqi(80.0)
    assert 151 <= aqi <= 200
    assert cat == "Unhealthy"


def test_compute_aqi_hazardous():
    aqi, cat = compute_aqi(350.0)
    assert aqi >= 301
    assert cat == "Hazardous"


def test_compute_dew_point():
    dp = compute_dew_point(72.0, 50.0)
    assert 50 < dp < 60


def test_station_reading_optional_fields():
    reading = StationReading(station_id="test")
    assert reading.weather is None
    assert reading.soil == []
