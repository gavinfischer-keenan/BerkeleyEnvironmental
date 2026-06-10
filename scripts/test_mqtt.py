#!/usr/bin/env python3
"""Publish synthetic sensor data for testing the environmental station."""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

TOPIC = "home/sensors/station/berkeley"


def generate_reading(diablo=False, smoke=False, rain=False):
    t = time.time()
    hour = datetime.now().hour
    base_temp = 60 + 8 * math.sin((hour - 6) * math.pi / 12)
    temp = base_temp + random.gauss(0, 2)
    humidity = max(15, min(95, 65 - (temp - 60) * 1.5 + random.gauss(0, 5)))
    pressure = 1013.25 + 3 * math.sin(t / 3600) + random.gauss(0, 0.5)
    wind_speed = max(0, 5 + random.gauss(0, 3))
    wind_dir = 270 + random.gauss(0, 30)
    wind_gust = wind_speed + random.uniform(0, 5)
    pm25 = max(0, 8 + random.gauss(0, 3))
    pm10 = pm25 * 1.5 + random.gauss(0, 2)
    soil_zones = [
        {"zone": "zone_front", "depth": "6in", "moisture_pct": round(35 + random.gauss(0, 5), 1)},
        {"zone": "zone_hillside", "depth": "12in", "moisture_pct": round(40 + random.gauss(0, 5), 1)},
        {"zone": "zone_garden_n", "depth": "6in", "moisture_pct": round(30 + random.gauss(0, 5), 1)},
        {"zone": "zone_garden_s", "depth": "6in", "moisture_pct": round(32 + random.gauss(0, 5), 1)},
    ]
    rain_rate, rain_acc = 0.0, 0.0

    if diablo:
        wind_speed = 30 + random.gauss(0, 5)
        wind_dir = 45 + random.gauss(0, 10)
        wind_gust = wind_speed + random.uniform(5, 15)
        humidity = 15 + random.gauss(0, 3)
        for s in soil_zones:
            s["moisture_pct"] = round(20 + random.gauss(0, 3), 1)
    if smoke:
        pm25 = 150 + random.gauss(0, 30)
        pm10 = pm25 * 1.3 + random.gauss(0, 10)
    if rain:
        rain_rate = 25 + random.gauss(0, 5)
        rain_acc = 60 + random.gauss(0, 10)
        humidity = 90 + random.gauss(0, 3)
        for s in soil_zones:
            s["moisture_pct"] = min(98, s["moisture_pct"] + 40)

    for s in soil_zones:
        s["moisture_pct"] = round(max(5, min(100, s["moisture_pct"])), 1)

    return {
        "station_id": "berkeley-hilltop",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "firmware": "0.1.0-test",
        "weather": {"temperature": round(max(30, min(110, temp)), 1),
                     "humidity": round(max(5, min(100, humidity)), 1),
                     "pressure": round(pressure, 2)},
        "wind": {"speed_mph": round(max(0, wind_speed), 1),
                 "direction_deg": round(wind_dir % 360, 1),
                 "gust_mph": round(max(0, wind_gust), 1)},
        "air": {"pm25": round(max(0, pm25), 1), "pm10": round(max(0, pm10), 1)},
        "soil": soil_zones,
        "rain": {"rate_mm_hr": round(max(0, rain_rate), 1),
                 "accumulation_mm": round(max(0, rain_acc), 1)},
    }


def main():
    parser = argparse.ArgumentParser(description="Publish synthetic sensor data")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--diablo", action="store_true", help="Simulate Diablo winds")
    parser.add_argument("--smoke", action="store_true", help="Simulate wildfire smoke")
    parser.add_argument("--rain", action="store_true", help="Simulate atmospheric river")
    args = parser.parse_args()

    client = mqtt.Client(client_id="envstation-test-publisher")
    client.connect(args.broker, args.port)
    client.loop_start()

    modes = []
    if args.diablo: modes.append("DIABLO")
    if args.smoke: modes.append("SMOKE")
    if args.rain: modes.append("RAIN")
    print(f"Publishing to {args.broker}:{args.port} mode={'|'.join(modes) or 'NORMAL'}")

    try:
        while True:
            r = generate_reading(diablo=args.diablo, smoke=args.smoke, rain=args.rain)
            client.publish(TOPIC, json.dumps(r), qos=0)
            wx = r["weather"]
            print(f"  T={wx['temperature']}°F H={wx['humidity']}% Wind={r['wind']['speed_mph']}mph PM2.5={r['air']['pm25']}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
