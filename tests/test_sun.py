"""Tests for sunrise/sunset API."""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_sun_with_coords(client):
    # New York City
    resp = await client.get("/api/sun?lat=40.7128&lon=-74.006&date_str=2024-06-21")
    assert resp.status_code == 200
    data = resp.json()
    assert "sunrise" in data
    assert "sunset" in data
    assert "dawn" in data
    assert "dusk" in data
    assert "noon" in data
    assert data["day_length_hours"] > 14  # Summer solstice in NYC


@pytest.mark.anyio
async def test_sun_no_coords(client):
    resp = await client.get("/api/sun")
    assert resp.status_code == 200
    data = resp.json()
    # Should return error if no coords configured
    if "error" in data:
        assert "coordinates" in data["error"].lower() or "lat" in data["error"].lower()
