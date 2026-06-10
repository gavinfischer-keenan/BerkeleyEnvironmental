"""InfluxDB bucket creation and downsampling task management."""
from __future__ import annotations

import structlog
from influxdb_client import InfluxDBClient
from influxdb_client.domain.bucket_retention_rules import BucketRetentionRules

from envstation.config import get_config

log = structlog.get_logger(__name__)

_BUCKETS = {
    "sensors-raw":    30 * 86400,
    "sensors-hourly": 365 * 86400,
    "sensors-daily":  0,
}


def ensure_buckets(client: InfluxDBClient) -> None:
    cfg = get_config()
    buckets_api = client.buckets_api()
    existing = {b.name for b in (buckets_api.find_buckets().buckets or [])}
    for name, retention_sec in _BUCKETS.items():
        if name in existing:
            continue
        rules = [BucketRetentionRules(type="expire", every_seconds=retention_sec)] if retention_sec else []
        buckets_api.create_bucket(bucket_name=name, retention_rules=rules, org=cfg.influxdb_org)
        log.info("influx.bucket_created", name=name, retention_days=retention_sec // 86400 if retention_sec else "forever")


_DOWNSAMPLE_HOURLY = '''option task = {{name: "downsample_hourly", every: 1h}}
from(bucket: "{raw}")
  |> range(start: -task.every)
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
  |> to(bucket: "{hourly}", org: "{org}")
'''

_DOWNSAMPLE_DAILY = '''option task = {{name: "downsample_daily", every: 1d}}
from(bucket: "{hourly}")
  |> range(start: -task.every)
  |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
  |> to(bucket: "{daily}", org: "{org}")
'''


def create_downsampling_tasks(client: InfluxDBClient) -> None:
    cfg = get_config()
    tasks_api = client.tasks_api()
    existing = {t.name for t in (tasks_api.find_tasks() or [])}
    for name, template in [("downsample_hourly", _DOWNSAMPLE_HOURLY),
                           ("downsample_daily", _DOWNSAMPLE_DAILY)]:
        if name in existing:
            continue
        flux = template.format(raw=cfg.influxdb_bucket_raw, hourly=cfg.influxdb_bucket_hourly,
                               daily=cfg.influxdb_bucket_daily, org=cfg.influxdb_org)
        tasks_api.create_task_every(name=name, flux=flux,
                                   every="1h" if "hourly" in name else "1d",
                                   organization=client.org)
        log.info("influx.task_created", name=name)
