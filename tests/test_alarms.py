"""Tests for alarms API."""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_alarm_lifecycle(client):
    # Create
    resp = await client.post("/api/alarms", json={
        "label": "Test Alarm", "time_str": "08:30",
        "recurring": True, "days": [0, 2, 4],
    })
    assert resp.status_code == 200
    aid = resp.json()["id"]

    # List
    resp = await client.get("/api/alarms")
    assert resp.status_code == 200
    alarms = resp.json()
    alarm = next(a for a in alarms if a["id"] == aid)
    assert alarm["label"] == "Test Alarm"
    assert alarm["time"] == "08:30"
    assert alarm["recurring"] is True
    assert alarm["days"] == [0, 2, 4]

    # Toggle
    resp = await client.patch(f"/api/alarms/{aid}")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    # Toggle back
    resp = await client.patch(f"/api/alarms/{aid}")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True

    # Delete
    resp = await client.delete(f"/api/alarms/{aid}")
    assert resp.status_code == 200
