"""Tests for the Rachio API client."""
from __future__ import annotations

import asyncio

import pytest

from envstation.integrations.rachio import RachioClient


def test_auth_header():
    client = RachioClient(api_key="test-api-key-123", device_id="dev-1")
    assert client._headers["Authorization"] == "Bearer test-api-key-123"


def test_rate_limit_tracking():
    client = RachioClient(api_key="test", device_id="dev-1")
    assert client.requests_today == 0
    client.requests_today += 1
    assert client.requests_today == 1


def test_daily_limit():
    assert RachioClient.DAILY_LIMIT == 3500


def test_base_url():
    assert RachioClient.BASE_URL == "https://api.rach.io/1/public"


def test_no_device_raises():
    client = RachioClient(api_key="test")
    with pytest.raises(ValueError, match="No device_id"):
        asyncio.run(client.stop_all())
