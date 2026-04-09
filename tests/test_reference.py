"""Tests for timezone reference and DST APIs."""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_list_timezones(client):
    resp = await client.get("/api/reference/timezones")
    assert resp.status_code == 200
    zones = resp.json()
    assert len(zones) > 100  # IANA has ~400+ zones
    assert "timezone" in zones[0]
    assert "abbreviation" in zones[0]
    assert "utc_offset" in zones[0]


@pytest.mark.anyio
async def test_filter_timezones(client):
    resp = await client.get("/api/reference/timezones?filter=America")
    assert resp.status_code == 200
    zones = resp.json()
    assert all("America" in z["timezone"] for z in zones)


@pytest.mark.anyio
async def test_dst_transitions_with_dst(client):
    resp = await client.get("/api/reference/dst/America/New_York?year=2024")
    assert resp.status_code == 200
    data = resp.json()
    assert data["observes_dst"] is True
    assert len(data["transitions"]) == 2  # spring forward, fall back


@pytest.mark.anyio
async def test_dst_transitions_without_dst(client):
    resp = await client.get("/api/reference/dst/Asia/Tokyo?year=2024")
    assert resp.status_code == 200
    data = resp.json()
    assert data["observes_dst"] is False
    assert len(data["transitions"]) == 0
