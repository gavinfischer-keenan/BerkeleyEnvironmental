"""MQTT publisher for alerts and commands to the home intelligence bus."""
from __future__ import annotations

import json

import paho.mqtt.client as mqtt
import structlog

log = structlog.get_logger(__name__)


class MQTTPublisher:
    def __init__(self, broker: str, port: int, client_id: str = "envstation-publisher") -> None:
        self.broker = broker
        self.port = port
        self._client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        self._connected = False

    def start(self) -> None:
        self._client.connect(self.broker, self.port, keepalive=60)
        self._client.loop_start()
        self._connected = True
        log.info("mqtt_publisher.started", broker=self.broker)

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
        self._connected = False

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
