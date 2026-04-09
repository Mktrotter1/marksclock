"""Tests for meeting planner API."""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_meeting_overlap_found(client):
    resp = await client.post("/api/meeting/overlap", json={
        "timezones": ["America/New_York", "Europe/London"],
        "work_start": "09:00",
        "work_end": "17:00",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["overlap"] is True
    assert data["overlap_hours"] > 0
    assert len(data["per_zone"]) == 2


@pytest.mark.anyio
async def test_meeting_no_overlap(client):
    # New York (UTC-5/4) vs Tokyo (UTC+9) with narrow hours
    resp = await client.post("/api/meeting/overlap", json={
        "timezones": ["America/New_York", "Asia/Tokyo"],
        "work_start": "09:00",
        "work_end": "12:00",
    })
    assert resp.status_code == 200
    data = resp.json()
    # With 3-hour windows 14 hours apart, there's no overlap
    assert data["overlap"] is False


@pytest.mark.anyio
async def test_meeting_three_timezones(client):
    resp = await client.post("/api/meeting/overlap", json={
        "timezones": ["America/New_York", "Europe/London", "Europe/Berlin"],
        "work_start": "09:00",
        "work_end": "17:00",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["overlap"] is True
    assert len(data["per_zone"]) == 3
