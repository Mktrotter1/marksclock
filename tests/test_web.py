"""Tests for the web UI API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.switch_manager import SwitchManager


@pytest.fixture
def client():
    # Import after fixture to reset global state
    from markslamp import web
    from markslamp.protocols.base import LampProtocol

    class StubProtocol(LampProtocol):
        name = "stub"

        async def discover(self, timeout=5.0):
            return [Lamp(id="stub:1", name="Stub Lamp", ip="10.0.0.1", port=80, protocol="stub")]

        async def connect(self, lamp):
            lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=True))
            lamp.add_switch(Switch("brightness", SwitchType.RANGE, value=128, min_val=0, max_val=255))
            lamp.connected = True
            return True

        async def set_switch(self, lamp, switch_name, value):
            if switch_name in lamp.switches:
                lamp.switches[switch_name].value = value
                return True
            return False

        async def get_state(self, lamp):
            return {}

    # Pre-populate manager
    mgr = SwitchManager([StubProtocol()])
    lamp = Lamp(id="stub:1", name="Stub Lamp", ip="10.0.0.1", port=80, protocol="stub")
    lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=True))
    lamp.add_switch(Switch("brightness", SwitchType.RANGE, value=128, min_val=0, max_val=255))
    lamp.connected = True
    mgr.register_lamp(lamp)
    web._mgr = mgr

    return TestClient(web.app)


def test_index_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "markslamp" in resp.text
    assert "<!DOCTYPE html>" in resp.text


def test_api_lamps(client):
    resp = client.get("/api/lamps")
    assert resp.status_code == 200
    data = resp.json()
    assert "lamps" in data
    assert "stub:1" in data["lamps"]
    lamp = data["lamps"]["stub:1"]
    assert lamp["name"] == "Stub Lamp"
    assert "power" in lamp["switches"]
    assert lamp["switches"]["power"]["type"] == "toggle"


def test_api_set_switch(client):
    resp = client.post("/api/switch", json={
        "lamp_id": "stub:1",
        "switch_name": "power",
        "value": False,
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_api_set_switch_brightness(client):
    resp = client.post("/api/switch", json={
        "lamp_id": "stub:1",
        "switch_name": "brightness",
        "value": 200,
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_api_set_switch_invalid_lamp(client):
    resp = client.post("/api/switch", json={
        "lamp_id": "nonexistent",
        "switch_name": "power",
        "value": True,
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


def test_api_toggle(client):
    resp = client.post("/api/toggle/stub:1")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_api_refresh(client):
    resp = client.get("/api/refresh/stub:1")
    assert resp.status_code == 200
    assert "state" in resp.json()
