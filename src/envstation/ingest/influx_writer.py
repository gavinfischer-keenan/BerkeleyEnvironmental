"""Write sensor readings to InfluxDB as time-series points."""
from __future__ import annotations

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import structlog

from envstation.ingest.schema import StationReading

log = structlog.get_logger(__name__)


class InfluxWriter:
    """Converts StationReadings to InfluxDB Points and writes them."""

    def __init__(self, url: str, token: str, org: str, bucket: str) -> None:
        self.org = org
        self.bucket = bucket
        self._client = InfluxDBClient(url=url, token=token, org=org)
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)

    def write_reading(self, reading: StationReading) -> None:
        points = self._reading_to_points(reading)
        if not points:
            return
        try:
            self._write_api.write(bucket=self.bucket, record=points)
            log.debug("influx.written", count=len(points), station=reading.station_id)
        except Exception:
            log.exception("influx.write_failed", station=reading.station_id)

    def _reading_to_points(self, r: StationReading) -> list[Point]:
        ts, station = r.timestamp, r.station_id
        points: list[Point] = []
        if r.weather:
            points.append(
                Point("weather").tag("station", station)
                .field("temperature", r.weather.temperature)
                .field("humidity", r.weather.humidity)
                .field("pressure", r.weather.pressure)
                .field("dew_point", r.weather.dew_point)
                .time(ts, WritePrecision.S))
        if r.wind:
            points.append(
                Point("wind").tag("station", station)
                .field("speed_mph", r.wind.speed_mph)
                .field("direction_deg", r.wind.direction_deg)
                .field("gust_mph", r.wind.gust_mph)
                .time(ts, WritePrecision.S))
        if r.air:
            points.append(
                Point("air_quality").tag("station", station)
                .field("pm25", r.air.pm25).field("pm10", r.air.pm10)
                .field("aqi", r.air.aqi).field("aqi_category", r.air.aqi_category)
                .time(ts, WritePrecision.S))
        for soil in r.soil:
            p = (Point("soil").tag("station", station)
                 .tag("zone", soil.zone).tag("depth", soil.depth)
                 .field("moisture_pct", soil.moisture_pct).time(ts, WritePrecision.S))
            if soil.temp_f is not None:
                p = p.field("temp_f", soil.temp_f)
            points.append(p)
        if r.rain:
            p = (Point("rain").tag("station", station)
                 .field("rate_mm_hr", r.rain.rate_mm_hr)
                 .field("accumulation_mm", r.rain.accumulation_mm)
                 .time(ts, WritePrecision.S))
            if r.rain.tips_total is not None:
                p = p.field("tips_total", r.rain.tips_total)
            points.append(p)
        return points

    def close(self) -> None:
        self._client.close()
