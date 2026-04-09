"""Tests for stopwatch API."""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_stopwatch_lifecycle(client):
    # Reset first
    resp = await client.post("/api/stopwatch/reset")
    assert resp.status_code == 200

    # Get state
    resp = await client.get("/api/stopwatch")
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"
    assert resp.json()["elapsed"] == 0.0

    # Start
    resp = await client.post("/api/stopwatch/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"

    # Lap
    resp = await client.post("/api/stopwatch/lap")
    assert resp.status_code == 200
    assert len(resp.json()["laps"]) >= 1

    # Stop
    resp = await client.post("/api/stopwatch/stop")
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"

    # Reset
    resp = await client.post("/api/stopwatch/reset")
    assert resp.status_code == 200
    assert resp.json()["elapsed"] == 0.0
    assert resp.json()["laps"] == []
