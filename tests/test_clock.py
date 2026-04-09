"""Tests for clock API."""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_clock_default(client):
    resp = await client.get("/api/clock")
    assert resp.status_code == 200
    data = resp.json()
    assert "time_24h" in data
    assert "time_12h" in data
    assert "iso" in data
    assert "epoch" in data
    assert "day_of_week" in data
    assert "week_number" in data


@pytest.mark.anyio
async def test_clock_with_timezone(client):
    resp = await client.get("/api/clock?tz=Europe/London")
    assert resp.status_code == 200
    data = resp.json()
    assert data["timezone"] == "Europe/London"
