"""Tests for world clock API."""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_worldclock_list(client):
    resp = await client.get("/api/worldclock")
    assert resp.status_code == 200
    zones = resp.json()
    assert len(zones) >= 1
    assert "timezone" in zones[0]
    assert "time_24h" in zones[0]


@pytest.mark.anyio
async def test_worldclock_add_remove(client):
    # Add
    resp = await client.post("/api/worldclock", json={"timezone": "Pacific/Auckland"})
    assert resp.status_code == 200
    assert "Pacific/Auckland" in resp.json()["zones"]

    # List should include it
    resp = await client.get("/api/worldclock")
    assert any(z["timezone"] == "Pacific/Auckland" for z in resp.json())

    # Remove
    resp = await client.delete("/api/worldclock/Pacific/Auckland")
    assert resp.status_code == 200
    assert "Pacific/Auckland" not in resp.json()["zones"]
