"""Tests for pomodoro API."""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_pomodoro_lifecycle(client):
    # Reset
    resp = await client.post("/api/pomodoro/reset")
    assert resp.status_code == 200
    assert resp.json()["phase"] == "idle"

    # Start
    resp = await client.post("/api/pomodoro/start")
    assert resp.status_code == 200
    assert resp.json()["phase"] == "work"
    assert resp.json()["remaining"] > 0

    # Pause
    resp = await client.post("/api/pomodoro/pause")
    assert resp.status_code == 200

    # Skip to break
    resp = await client.post("/api/pomodoro/skip")
    assert resp.status_code == 200
    assert resp.json()["phase"] in ("short_break", "long_break")

    # Skip back to work
    resp = await client.post("/api/pomodoro/skip")
    assert resp.status_code == 200
    assert resp.json()["phase"] == "work"

    # Reset
    resp = await client.post("/api/pomodoro/reset")
    assert resp.json()["phase"] == "idle"


@pytest.mark.anyio
async def test_pomodoro_config(client):
    # Get config
    resp = await client.get("/api/pomodoro/config")
    assert resp.status_code == 200
    assert "work_minutes" in resp.json()

    # Update config
    resp = await client.put("/api/pomodoro/config", json={
        "work_minutes": 30,
        "short_break_minutes": 10,
        "long_break_minutes": 20,
        "sessions_before_long": 3,
    })
    assert resp.status_code == 200
    assert resp.json()["work_minutes"] == 30

    # Restore defaults
    await client.put("/api/pomodoro/config", json={
        "work_minutes": 25, "short_break_minutes": 5,
        "long_break_minutes": 15, "sessions_before_long": 4,
    })
