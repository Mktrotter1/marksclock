"""Tests for timer API."""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_timer_lifecycle(client):
    # Create
    resp = await client.post("/api/timers", json={"label": "Test", "duration_seconds": 300})
    assert resp.status_code == 200
    tid = resp.json()["id"]

    # List
    resp = await client.get("/api/timers")
    assert resp.status_code == 200
    timers = resp.json()
    assert any(t["id"] == tid for t in timers)

    # Start
    resp = await client.post(f"/api/timers/{tid}/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"

    # Pause
    resp = await client.post(f"/api/timers/{tid}/pause")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"

    # Reset
    resp = await client.post(f"/api/timers/{tid}/reset")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"

    # Delete
    resp = await client.delete(f"/api/timers/{tid}")
    assert resp.status_code == 200
