"""Soil saturation rules — irrigation control + hillside stability."""
from __future__ import annotations

import structlog

from envstation.config import Config
from envstation.ingest.schema import SoilReading

log = structlog.get_logger(__name__)


def evaluate_soil(soil_readings: list[SoilReading], config: Config) -> tuple[list, list]:
    from envstation.rules.engine import Alert, IrrigationCommand

    alerts: list[Alert] = []
    irrigation: list[IrrigationCommand] = []

    for soil in soil_readings:
        pct, zone = soil.moisture_pct, soil.zone

        if pct >= config.soil_critical_threshold:
            alerts.append(Alert(
                alert_type=f"soil_critical_{zone}", severity="critical",
                title="🚨 SLOPE INSTABILITY RISK",
                message=f"Zone '{zone}' at {pct:.0f}% saturation. Critical drainage required.",
                data={"zone": zone, "moisture_pct": pct, "depth": soil.depth}))
        elif pct >= config.soil_wet_threshold:
            alerts.append(Alert(
                alert_type=f"soil_saturated_{zone}", severity="warning",
                title="⚠️ High Soil Saturation",
                message=f"Zone '{zone}' at {pct:.0f}%. Monitoring hillside stability.",
                data={"zone": zone, "moisture_pct": pct, "depth": soil.depth}))
        elif pct <= config.soil_dry_threshold:
            irrigation.append(IrrigationCommand(
                zone=zone, action="start", duration_sec=600,
                reason=f"Soil moisture at {pct:.0f}% (threshold: {config.soil_dry_threshold}%)"))
            log.info("soil.irrigation_triggered", zone=zone, moisture_pct=pct)

    return alerts, irrigation
