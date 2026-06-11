"""MQTT publisher for alerts and commands to the home intelligence bus.

Follows the standard Berkeley agent lifecycle:
  start()  → publishes online status (retained)
  stop()   → publishes offline status (retained)

Topic schema:
  home/alerts/{alert-type}       — urgent alerts (QoS 1)
  home/status/environmental-station — heartbeat (QoS 0, retained)
  home/commands/{target}         — display/alexa commands (QoS 1)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import structlog

from envstation import __version__

log = structlog.get_logger(__name__)

TOPIC_STATUS = "home/status/environmental-station"


class MQTTPublisher:
    def __init__(self, broker: str, port: int, client_id: str = "envstation-publisher") -> None:
        self.broker = broker
        self.port = port
        self._client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        self._connected = False
        # Last Will and Testament — marks agent offline if connection drops
        self._client.will_set(
            TOPIC_STATUS,
            json.dumps({"status": "offline", "agent": "environmental-station"}),
            qos=1, retain=True,
        )

    def start(self) -> None:
        self._client.connect(self.broker, self.port, keepalive=60)
        self._client.loop_start()
        self._connected = True
        # Standard agent lifecycle: publish online status
        self._publish(TOPIC_STATUS, {
            "status": "online",
            "agent": "environmental-station",
            "version": __version__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, qos=1, retain=True)
        log.info("mqtt_publisher.started", broker=self.broker)

    def stop(self) -> None:
        # Standard agent lifecycle: publish offline status before disconnect
        self._publish(TOPIC_STATUS, {
            "status": "offline",
            "agent": "environmental-station",
            "version": __version__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, qos=1, retain=True)
        self._client.loop_stop()
        self._client.disconnect()
        self._connected = False
        log.info("mqtt_publisher.stopped")

    def _publish(self, topic: str, payload: dict, qos: int = 1, retain: bool = False) -> None:
        if not self._connected:
            log.warning("mqtt_publisher.not_connected")
            return
        self._client.publish(topic, json.dumps(payload, default=str), qos=qos, retain=retain)

    def publish_alert(self, topic: str, alert) -> None:
        self._publish(topic, {
            "alert_id": alert.alert_id, "alert_type": alert.alert_type,
            "severity": alert.severity, "title": alert.title,
            "message": alert.message, "data": alert.data,
            "timestamp": alert.timestamp.isoformat()})

    def alert_fire_weather(self, alert) -> None:
        self.publish_alert("home/alerts/fire-weather", alert)

    def alert_air_quality(self, alert) -> None:
        self.publish_alert("home/alerts/air-quality", alert)

    def alert_soil_saturation(self, alert) -> None:
        self.publish_alert("home/alerts/soil-saturation", alert)

    def alert_rain(self, alert) -> None:
        self.publish_alert("home/alerts/heavy-rain", alert)

    def publish_command(self, target: str, command: dict) -> None:
        self._publish(f"home/commands/{target}", command)

    def command_alexa_say(self, text: str) -> None:
        self.publish_command("alexa-say", {"text": text})

    def command_display(self, command: str, data: dict | None = None) -> None:
        self.publish_command("display", {"command": command, **(data or {})})
