"""Tests for converter/calculator APIs."""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_timezone_convert(client):
    resp = await client.post("/api/convert/timezone", json={
        "time_iso": "2024-06-15T12:00:00",
        "from_tz": "America/New_York",
        "to_tz": "Europe/London",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "to" in data
    assert "Europe/London" in data["to"]["timezone"]


@pytest.mark.anyio
async def test_unix_timestamp_to_iso(client):
    resp = await client.post("/api/convert/unix", json={"timestamp": 1700000000})
    assert resp.status_code == 200
    data = resp.json()
    assert "iso" in data
    assert "2023-11-14" in data["iso"]


@pytest.mark.anyio
async def test_unix_iso_to_timestamp(client):
    resp = await client.post("/api/convert/unix", json={"iso": "2024-01-01T00:00:00+00:00"})
    assert resp.status_code == 200
    assert resp.json()["timestamp"] == 1704067200.0


@pytest.mark.anyio
async def test_duration_calc(client):
    resp = await client.post("/api/convert/duration", json={
        "start": "2024-01-01T00:00:00",
        "end": "2024-01-03T12:30:00",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["days"] == 2
    assert data["hours"] == 12
    assert data["minutes"] == 30


@pytest.mark.anyio
async def test_date_add(client):
    resp = await client.post("/api/convert/date-add", json={
        "date": "2024-01-15", "months": 2, "days": 10,
    })
    assert resp.status_code == 200
    assert "2024-03-25" in resp.json()["result"]


@pytest.mark.anyio
async def test_leap_year(client):
    resp = await client.get("/api/convert/leap-year?year=2024")
    assert resp.status_code == 200
    assert resp.json()["is_leap_year"] is True

    resp = await client.get("/api/convert/leap-year?year=2023")
    assert resp.json()["is_leap_year"] is False

    resp = await client.get("/api/convert/leap-year?year=1900")
    assert resp.json()["is_leap_year"] is False

    resp = await client.get("/api/convert/leap-year?year=2000")
    assert resp.json()["is_leap_year"] is True


@pytest.mark.anyio
async def test_day_of_week(client):
    resp = await client.get("/api/convert/day-of-week?date=2024-07-04")
    assert resp.status_code == 200
    assert resp.json()["day_of_week"] == "Thursday"


@pytest.mark.anyio
async def test_week_number(client):
    resp = await client.get("/api/convert/week-number?date=2024-01-01")
    assert resp.status_code == 200
    assert "iso_week" in resp.json()


@pytest.mark.anyio
async def test_age(client):
    resp = await client.get("/api/convert/age?birthdate=1990-06-15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["years"] >= 35
    assert "human" in data


@pytest.mark.anyio
async def test_days_between(client):
    resp = await client.get("/api/convert/days-between?start=2024-01-01&end=2024-12-31")
    assert resp.status_code == 200
    assert resp.json()["days"] == 365
