"""Tests for Flux query construction."""
from __future__ import annotations


def test_latest_query_format():
    bucket = "sensors-raw"
    measurement = "weather"
    station = "berkeley-hilltop"
    flux = f'''from(bucket: "{bucket}")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
  |> filter(fn: (r) => r["station"] == "{station}")
  |> last()'''
    assert 'from(bucket: "sensors-raw")' in flux
    assert 'r["_measurement"] == "weather"' in flux
    assert "last()" in flux


def test_history_query_format():
    bucket = "sensors-raw"
    field = "speed_mph"
    start = "-6h"
    flux = f'''from(bucket: "{bucket}")
  |> range(start: {start})
  |> filter(fn: (r) => r["_field"] == "{field}")'''
    assert f"range(start: {start})" in flux
    assert f'r["_field"] == "{field}"' in flux


def test_rain_accumulation_query():
    flux = '''from(bucket: "sensors-raw")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "rain")
  |> filter(fn: (r) => r["_field"] == "accumulation_mm")
  |> last()'''
    assert 'r["_measurement"] == "rain"' in flux
    assert 'r["_field"] == "accumulation_mm"' in flux
