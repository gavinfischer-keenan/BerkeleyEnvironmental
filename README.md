# Berkeley Environmental Monitoring Station

Server-side platform for the Berkeley Hills home intelligence system. Ingests environmental sensor data from a Raspberry Pi station via MQTT, stores time-series data in InfluxDB, runs intelligent alert rules, controls Rachio irrigation, and feeds the Berkeley Dashboard.

## Architecture

```
Raspberry Pi Station → MQTT (Mosquitto) → envstation
                                            ├── InfluxDB (time-series storage)
                                            ├── Rules Engine (alerts)
                                            ├── Rachio API (irrigation control)
                                            ├── Dashboard (HTTP POST)
                                            └── REST API (queries)
```

## Sensor Suite

| Sensor | Measurements | Purpose |
|--------|-------------|---------|
| Anemometer + Vane | Wind speed, direction, gust | Diablo wind detection |
| PMS5003 | PM2.5, PM10 | Wildfire smoke detection |
| BME280 | Temperature, humidity, pressure | Weather monitoring |
| Soil Probes (×4-6) | Moisture %, temperature | Irrigation + slope stability |
| Rain Gauge | Rate mm/hr, accumulation | Atmospheric river detection |

## Alert Rules

- **Diablo Wind**: Offshore NE-E wind >25 mph + humidity <20% → fire weather alert + pre-hydration
- **Air Quality**: PM2.5/AQI thresholds → HVAC filtration alerts
- **Soil Saturation**: >85% → hillside stability warning; <25% → Rachio irrigation
- **Heavy Rain**: >10 mm/hr → drain clearing alert; >25 mm/hr → atmospheric river
- **Fire Weather Composite**: All conditions met → critical alert + pre-hydration of all zones

## Quick Start

```bash
git clone https://github.com/gavinfischer-keenan/BerkeleyEnvironmental.git
cd BerkeleyEnvironmental
python -m venv venv && source venv/bin/activate
pip install -e .

cp .env.example .env
# Edit .env with your InfluxDB token, Rachio API key, MQTT broker

envstation setup-influxdb
envstation run
```

## MQTT Topic Schema

```
home/sensors/station/berkeley    ← Batch readings from Pi
home/alerts/fire-weather         → Fire weather alerts
home/alerts/air-quality          → PM2.5/AQI alerts
home/alerts/soil-saturation      → Slope stability alerts
home/commands/display            → Dashboard overlay commands
home/commands/alexa-say          → Alexa TTS commands
```

## REST API (port 8090)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Service health |
| `GET /readings/latest` | Latest from all sensors |
| `GET /history/{measurement}/{field}` | Time-series data |
| `GET /alerts` | Active alerts |
| `GET /rachio/status` | Rachio device info |
| `POST /rachio/zone/{id}/start` | Start irrigation zone |

## Testing

```bash
pip install -e ".[dev]"
pytest tests/

# Simulate sensor data
python scripts/test_mqtt.py
python scripts/test_mqtt.py --diablo   # Simulate Diablo winds
python scripts/test_mqtt.py --smoke    # Simulate wildfire smoke
python scripts/test_mqtt.py --rain     # Simulate atmospheric river
```
