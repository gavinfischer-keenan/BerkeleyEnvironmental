"""MQTT subscriber — ingests sensor readings from the Raspberry Pi station."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

import paho.mqtt.client as mqtt
import structlog

from envstation.ingest.schema import (
    AirQualityReading, RainReading, SoilReading, StationReading,
    WeatherReading, WindReading,
)

log = structlog.get_logger(__name__)


class MQTTSubscriber:
    """Subscribe to environmental sensor topics and parse readings."""

    def __init__(self, broker: str, port: int, topic_prefix: str,
                 on_reading: Callable[[StationReading], Any],
                 client_id: str = "envstation-subscriber") -> None:
        self.broker = broker
        self.port = port
        self.topic_prefix = topic_prefix.rstrip("/")
        self.on_reading = on_reading
        self.messages_received: int = 0
        self.last_message_time: datetime | None = None
        self.connected: bool = False

        self._client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.will_set(
            "home/status/environmental-station",
            json.dumps({"status": "offline"}), qos=1, retain=True,
        )

    def start(self) -> None:
        log.info("mqtt.connecting", broker=self.broker, port=self.port)
        self._client.connect(self.broker, self.port, keepalive=60)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.publish("home/status/environmental-station",
                             json.dumps({"status": "offline"}), qos=1, retain=True)
        self._client.loop_stop()
        self._client.disconnect()
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            client.subscribe(f"{self.topic_prefix}/#", qos=0)
            client.publish("home/status/environmental-station",
                           json.dumps({"status": "online"}), qos=1, retain=True)
            log.info("mqtt.connected")
        else:
            log.error("mqtt.connect_failed", rc=rc)

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        log.warning("mqtt.disconnected", rc=rc)

    def _on_message(self, client, userdata, msg):
        self.messages_received += 1
        self.last_message_time = datetime.now(timezone.utc)
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if "/station/" in msg.topic:
                reading = self._parse_batch(payload)
            else:
                reading = self._parse_individual(msg.topic, payload)
            if reading:
                self.on_reading(reading)
        except Exception:
            log.exception("mqtt.parse_error", topic=msg.topic)

    def _parse_batch(self, payload: dict) -> StationReading:
        kwargs: dict[str, Any] = {
            "station_id": payload.get("station_id", "berkeley-hilltop"),
            "firmware": payload.get("firmware"), "uptime_s": payload.get("uptime_s"),
        }
        if "timestamp" in payload:
            kwargs["timestamp"] = datetime.fromisoformat(payload["timestamp"])
        if payload.get("weather"):
            kwargs["weather"] = WeatherReading(**payload["weather"])
        if payload.get("wind"):
            kwargs["wind"] = WindReading(**payload["wind"])
        if payload.get("air"):
            kwargs["air"] = AirQualityReading(**payload["air"])
        if payload.get("soil"):
            kwargs["soil"] = [SoilReading(**s) for s in payload["soil"]]
        if payload.get("rain"):
            kwargs["rain"] = RainReading(**payload["rain"])
        return StationReading(**kwargs)

    def _parse_individual(self, topic: str, payload: dict) -> StationReading | None:
        parts = topic.replace(self.topic_prefix + "/", "").split("/")
        if len(parts) < 1:
            return None
        category = parts[0]
        kwargs: dict[str, Any] = {}
        if category == "weather":
            kwargs["weather"] = WeatherReading(**payload)
        elif category == "wind":
            kwargs["wind"] = WindReading(**payload)
        elif category == "air":
            kwargs["air"] = AirQualityReading(**payload)
        elif category == "soil":
            kwargs["soil"] = [SoilReading(**payload)]
        elif category == "rain":
            kwargs["rain"] = RainReading(**payload)
        else:
            return None
        return StationReading(**kwargs)
