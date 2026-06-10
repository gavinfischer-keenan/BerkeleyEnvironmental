#!/usr/bin/env bash
set -euo pipefail

echo "=== InfluxDB Setup for Environmental Station ==="

if ! command -v influx &>/dev/null; then
    echo "ERROR: 'influx' CLI not found. Install InfluxDB 2.x first."
    exit 1
fi

ORG="home"
RAW_BUCKET="sensors-raw"
HOURLY_BUCKET="sensors-hourly"
DAILY_BUCKET="sensors-daily"

influx org create --name "$ORG" 2>/dev/null || echo "Org '$ORG' already exists"
influx bucket create --name "$RAW_BUCKET" --retention 30d --org "$ORG" 2>/dev/null || echo "Bucket '$RAW_BUCKET' exists"
influx bucket create --name "$HOURLY_BUCKET" --retention 365d --org "$ORG" 2>/dev/null || echo "Bucket '$HOURLY_BUCKET' exists"
influx bucket create --name "$DAILY_BUCKET" --retention 0 --org "$ORG" 2>/dev/null || echo "Bucket '$DAILY_BUCKET' exists"

TOKEN=$(influx auth create \
    --org "$ORG" --description "envstation" \
    --read-bucket "$RAW_BUCKET" --write-bucket "$RAW_BUCKET" \
    --read-bucket "$HOURLY_BUCKET" --write-bucket "$HOURLY_BUCKET" \
    --read-bucket "$DAILY_BUCKET" --write-bucket "$DAILY_BUCKET" \
    --json | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

echo ""
echo "=== Setup complete ==="
echo "Add to .env:  INFLUXDB_TOKEN=$TOKEN"
