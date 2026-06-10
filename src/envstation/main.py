"""CLI entry point — starts all environmental station services."""
from __future__ import annotations

import argparse
import asyncio
import signal
import sys

import structlog

from envstation import __version__
from envstation.config import get_config

log = structlog.get_logger(__name__)


def _configure_logging(level: str) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog, level.upper(), structlog.INFO)),
    )


async def _run() -> None:
    cfg = get_config()
    _configure_logging(cfg.log_level)
    log.info("envstation.starting", version=__version__, station=cfg.station_id)

    from envstation.ingest.influx_writer import InfluxWriter
    from envstation.ingest.mqtt_subscriber import MQTTSubscriber
    from envstation.integrations.dashboard import DashboardClient
    from envstation.integrations.mqtt_publisher import MQTTPublisher
    from envstation.integrations.rachio import RachioClient
    from envstation.rules.engine import RulesEngine
    from envstation.telemetry.health import HealthMonitor
    from envstation.api.server import app, set_dependencies

    influx_writer = InfluxWriter(url=cfg.influxdb_url, token=cfg.influxdb_token,
                                 org=cfg.influxdb_org, bucket=cfg.influxdb_bucket_raw)
    health = HealthMonitor()
    dashboard = DashboardClient(cfg.dashboard_url)
    mqtt_pub = MQTTPublisher(cfg.mqtt_broker, cfg.mqtt_port)

    rachio: RachioClient | None = None
    if cfg.rachio_api_key:
        rachio = RachioClient(cfg.rachio_api_key, cfg.rachio_device_id or None)

    rules = RulesEngine(cfg)
    set_dependencies(rules_engine=rules, rachio_client=rachio, health_monitor=health)

    async def on_reading_async(reading):
        health.update_station_seen()
        health.mqtt_connected = True
        influx_writer.write_reading(reading)
        alerts, irrigation_cmds = rules.evaluate(reading)
        for alert in alerts:
            await dashboard.send_alert(alert)
            if "fire" in alert.alert_type:
                mqtt_pub.alert_fire_weather(alert)
                mqtt_pub.command_alexa_say(alert.message)
            elif "aqi" in alert.alert_type or "smoke" in alert.alert_type:
                mqtt_pub.alert_air_quality(alert)
            elif "soil" in alert.alert_type:
                mqtt_pub.alert_soil_saturation(alert)
            elif "rain" in alert.alert_type:
                mqtt_pub.alert_rain(alert)
            mqtt_pub.command_display("environment_alert", {
                "severity": alert.severity, "title": alert.title, "message": alert.message})
        if rachio and irrigation_cmds:
            zone_map = cfg.zone_mapping
            for cmd in irrigation_cmds:
                rachio_zone_id = zone_map.get(cmd.zone)
                if not rachio_zone_id:
                    log.warning("rachio.unmapped_zone", zone=cmd.zone)
                    continue
                try:
                    if cmd.action == "start":
                        await rachio.start_zone(rachio_zone_id, cmd.duration_sec)
                except Exception:
                    log.exception("rachio.command_failed", zone=cmd.zone)
        await dashboard.send_reading(reading)

    def on_reading(reading):
        asyncio.get_event_loop().call_soon_threadsafe(asyncio.ensure_future, on_reading_async(reading))

    mqtt_sub = MQTTSubscriber(broker=cfg.mqtt_broker, port=cfg.mqtt_port,
                              topic_prefix=cfg.mqtt_topic_prefix, on_reading=on_reading)
    mqtt_sub.start()
    mqtt_pub.start()

    shutdown_event = asyncio.Event()

    def _handle_signal(sig, frame):
        log.info("envstation.shutting_down", signal=sig)
        shutdown_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    import uvicorn
    server_config = uvicorn.Config(app, host="0.0.0.0", port=cfg.api_port, log_level="warning")
    server = uvicorn.Server(server_config)
    log.info("envstation.running", api_port=cfg.api_port, mqtt_broker=cfg.mqtt_broker)

    try:
        await asyncio.gather(server.serve(),
                             health.heartbeat_loop(cfg.heartbeat_interval_sec, mqtt_pub, dashboard))
    except asyncio.CancelledError:
        pass
    finally:
        mqtt_sub.stop()
        mqtt_pub.stop()
        influx_writer.close()
        log.info("envstation.stopped")


def cli() -> None:
    parser = argparse.ArgumentParser(prog="envstation", description="Berkeley Environmental Monitoring Station")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", help="Available commands")
    sub.add_parser("run", help="Start the environmental station (default)")
    sub.add_parser("test-rachio", help="Test Rachio API connectivity")
    sub.add_parser("test-mqtt", help="Test MQTT broker connectivity")
    sub.add_parser("setup-influxdb", help="Create InfluxDB buckets and tasks")

    args = parser.parse_args()
    command = args.command or "run"

    if command == "run":
        asyncio.run(_run())
    elif command == "test-rachio":
        asyncio.run(_test_rachio())
    elif command == "test-mqtt":
        _test_mqtt()
    elif command == "setup-influxdb":
        _setup_influxdb()


async def _test_rachio() -> None:
    cfg = get_config()
    _configure_logging("DEBUG")
    if not cfg.rachio_api_key:
        log.error("No RACHIO_API_KEY set")
        return
    from envstation.integrations.rachio import RachioClient
    client = RachioClient(cfg.rachio_api_key, cfg.rachio_device_id or None)
    person = await client.get_person()
    log.info("rachio.person", **person)


def _test_mqtt() -> None:
    cfg = get_config()
    _configure_logging("DEBUG")
    import paho.mqtt.client as mqtt
    client = mqtt.Client(client_id="envstation-test")
    client.connect(cfg.mqtt_broker, cfg.mqtt_port)
    log.info("mqtt.test_passed", broker=cfg.mqtt_broker)
    client.disconnect()


def _setup_influxdb() -> None:
    cfg = get_config()
    _configure_logging("INFO")
    from envstation.storage.client import get_influx_client
    from envstation.storage.retention import ensure_buckets, create_downsampling_tasks
    client = get_influx_client()
    ensure_buckets(client)
    create_downsampling_tasks(client)
    log.info("influxdb.setup_complete")


if __name__ == "__main__":
    cli()
