"""Tests for the alert rules engine."""
from __future__ import annotations

import pytest

from envstation.ingest.schema import (
    AirQualityReading, RainReading, SoilReading, WeatherReading, WindReading,
)
from envstation.rules.wind_rules import evaluate_wind, _wind_history
from envstation.rules.air_rules import evaluate_air, _pm25_history
from envstation.rules.soil_rules import evaluate_soil
from envstation.rules.rain_rules import evaluate_rain, _rain_history


class TestWindRules:
    def setup_method(self):
        _wind_history.clear()

    def test_diablo_critical(self, config):
        wind = WindReading(speed_mph=32.0, direction_deg=45.0, gust_mph=45.0)
        wx = WeatherReading(temperature=85.0, humidity=12.0, pressure=1010.0)
        for _ in range(120):
            _wind_history.append(32.0)
        alerts = evaluate_wind(wind, wx, config)
        assert any(a.severity == "critical" for a in alerts)

    def test_normal_no_alert(self, config):
        wind = WindReading(speed_mph=8.0, direction_deg=270.0, gust_mph=12.0)
        wx = WeatherReading(temperature=68.0, humidity=55.0, pressure=1013.0)
        alerts = evaluate_wind(wind, wx, config)
        assert len(alerts) == 0

    def test_offshore_info(self, config):
        wind = WindReading(speed_mph=18.0, direction_deg=50.0, gust_mph=22.0)
        wx = WeatherReading(temperature=75.0, humidity=40.0, pressure=1012.0)
        for _ in range(120):
            _wind_history.append(18.0)
        alerts = evaluate_wind(wind, wx, config)
        assert any(a.severity == "info" for a in alerts)


class TestAirRules:
    def setup_method(self):
        _pm25_history.clear()

    def test_smoke_warning(self, config):
        air = AirQualityReading(pm25=160.0, pm10=200.0)
        alerts = evaluate_air(air, config)
        assert any(a.severity in ("warning", "critical") for a in alerts)

    def test_hazardous(self, config):
        air = AirQualityReading(pm25=350.0, pm10=400.0)
        alerts = evaluate_air(air, config)
        assert any(a.severity == "critical" for a in alerts)

    def test_clean_no_alert(self, config):
        air = AirQualityReading(pm25=8.0, pm10=12.0)
        alerts = evaluate_air(air, config)
        assert len(alerts) == 0


class TestSoilRules:
    def test_dry_irrigation(self, config):
        soil = [SoilReading(zone="front", moisture_pct=18.0)]
        alerts, irrigation = evaluate_soil(soil, config)
        assert len(irrigation) >= 1
        assert irrigation[0].action == "start"

    def test_saturated_warning(self, config):
        soil = [SoilReading(zone="hillside", depth="12in", moisture_pct=90.0)]
        alerts, _ = evaluate_soil(soil, config)
        assert any(a.severity == "warning" for a in alerts)

    def test_critical_slope(self, config):
        soil = [SoilReading(zone="hillside", depth="12in", moisture_pct=96.0)]
        alerts, _ = evaluate_soil(soil, config)
        assert any(a.severity == "critical" for a in alerts)


class TestRainRules:
    def setup_method(self):
        _rain_history.clear()

    def test_heavy_rain(self, config):
        rain = RainReading(rate_mm_hr=15.0, accumulation_mm=25.0)
        alerts = evaluate_rain(rain, config)
        assert any(a.alert_type == "rain_heavy" for a in alerts)

    def test_extreme_rain(self, config):
        rain = RainReading(rate_mm_hr=30.0, accumulation_mm=60.0)
        alerts = evaluate_rain(rain, config)
        assert any(a.alert_type == "rain_extreme" for a in alerts)
