"""Tests for calendar API."""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_calendar_month(client):
    resp = await client.get("/api/calendar/2024/6")
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == 2024
    assert data["month"] == 6
    assert data["month_name"] == "June"
    assert data["days_in_month"] == 30
    assert len(data["weeks"]) >= 4
    # Each week has 7 days
    for week in data["weeks"]:
        assert len(week) == 7
        for day in week:
            assert "date" in day
            assert "day" in day
            assert "in_month" in day
            assert "iso_week" in day


@pytest.mark.anyio
async def test_calendar_february_leap(client):
    resp = await client.get("/api/calendar/2024/2")
    assert resp.status_code == 200
    assert resp.json()["days_in_month"] == 29


@pytest.mark.anyio
async def test_calendar_february_non_leap(client):
    resp = await client.get("/api/calendar/2023/2")
    assert resp.status_code == 200
    assert resp.json()["days_in_month"] == 28
