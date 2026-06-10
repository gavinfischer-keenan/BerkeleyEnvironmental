"""Alert rules engine — evaluates sensor readings against thresholds."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Awaitable

import structlog

from envstation.config import Config
from envstation.ingest.schema import StationReading

log = structlog.get_logger(__name__)


@dataclass
class Alert:
    alert_type: str
    severity: str  # 'info', 'warning', 'critical'
    title: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None


@dataclass
class IrrigationCommand:
    zone: str
    action: str  # 'start', 'stop', 'skip'
    duration_sec: int = 600
    reason: str = ""


@dataclass
class PreHydrationCommand:
    zones: list[str]
    duration_per_zone_sec: int = 900
    reason: str = ""


class RulesEngine:
    def __init__(self, config: Config,
                 alert_callback: Callable[[Alert], Awaitable[None]] | None = None) -> None:
        self.config = config
        self.alert_callback = alert_callback
        self.last_readings: dict[str, Any] = {}
        self.alert_history: list[Alert] = []
        self.active_alerts: set[str] = set()
        self._last_alert_time: dict[str, datetime] = {}

    def evaluate(self, reading: StationReading) -> tuple[list[Alert], list[IrrigationCommand]]:
        from envstation.rules.wind_rules import evaluate_wind
        from envstation.rules.air_rules import evaluate_air
        from envstation.rules.soil_rules import evaluate_soil
        from envstation.rules.rain_rules import evaluate_rain
        from envstation.rules.fire_weather import evaluate_fire_weather

        all_alerts: list[Alert] = []
        all_irrigation: list[IrrigationCommand] = []

        if reading.wind:
            all_alerts.extend(evaluate_wind(reading.wind, reading.weather, self.config))
        if reading.air:
            all_alerts.extend(evaluate_air(reading.air, self.config))
        if reading.soil:
            alerts, irrigation = evaluate_soil(reading.soil, self.config)
            all_alerts.extend(alerts)
            all_irrigation.extend(irrigation)
        if reading.rain:
            all_alerts.extend(evaluate_rain(reading.rain, self.config))

        fw_alerts, prehydration = evaluate_fire_weather(
            reading.wind, reading.weather, reading.soil, reading.rain, self.config)
        all_alerts.extend(fw_alerts)
        if prehydration:
            for zone in prehydration.zones:
                all_irrigation.append(IrrigationCommand(
                    zone=zone, action="start",
                    duration_sec=prehydration.duration_per_zone_sec,
                    reason=prehydration.reason))

        new_alerts = self._apply_cooldown(all_alerts)
        self.alert_history.extend(new_alerts)
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-500:]

        if reading.weather:
            self.last_readings["weather"] = reading.weather
        if reading.wind:
            self.last_readings["wind"] = reading.wind

        if new_alerts:
            log.info("rules.alerts", count=len(new_alerts),
                     types=[a.alert_type for a in new_alerts])
        return new_alerts, all_irrigation

    def _apply_cooldown(self, alerts: list[Alert]) -> list[Alert]:
        now = datetime.now(timezone.utc)
        cooldown = timedelta(seconds=self.config.alert_cooldown_sec)
        new: list[Alert] = []
        for alert in alerts:
            last = self._last_alert_time.get(alert.alert_type)
            if last and (now - last) < cooldown:
                continue
            self._last_alert_time[alert.alert_type] = now
            new.append(alert)
        return new

    def get_active_alerts(self) -> list[Alert]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        return [a for a in self.alert_history if a.timestamp > cutoff]
