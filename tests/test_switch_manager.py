"""Tests for the switch manager."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol
from markslamp.switch_manager import SwitchManager


class MockProtocol(LampProtocol):
    name = "mock"

    def __init__(self):
        self.last_set: tuple[str, str, Any] | None = None
        self.set_result = True

    async def discover(self, timeout: float = 5.0) -> list[Lamp]:
        return []

    async def connect(self, lamp: Lamp) -> bool:
        return True

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        self.last_set = (lamp.id, switch_name, value)
        if self.set_result and switch_name in lamp.switches:
            lamp.switches[switch_name].value = value
        return self.set_result

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        return {n: s.value for n, s in lamp.switches.items()}


def _make_connected_lamp() -> Lamp:
    lamp = Lamp(id="mock:1", name="Test Lamp", ip="10.0.0.1", port=80, protocol="mock")
    lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=False))
    lamp.add_switch(Switch("brightness", SwitchType.RANGE, value=100, min_val=0, max_val=255))
    lamp.add_switch(Switch("color", SwitchType.COLOR, value=[255, 255, 255]))
    lamp.add_switch(Switch("effect", SwitchType.SELECT, value="none", options=["none", "rainbow"]))
    lamp.connected = True
    return lamp


@pytest.fixture
def mgr_and_proto():
    proto = MockProtocol()
    mgr = SwitchManager([proto])
    lamp = _make_connected_lamp()
    mgr.register_lamp(lamp)
    return mgr, proto


@pytest.mark.asyncio
async def test_register_lamp(mgr_and_proto):
    mgr, _ = mgr_and_proto
    assert len(mgr.lamps) == 1
    assert "mock:1" in mgr.lamps


@pytest.mark.asyncio
async def test_set_switch_power(mgr_and_proto):
    mgr, proto = mgr_and_proto
    ok = await mgr.set_switch("mock:1", "power", True)
    assert ok is True
    assert proto.last_set == ("mock:1", "power", True)
    assert mgr.lamps["mock:1"].switches["power"].value is True


@pytest.mark.asyncio
async def test_set_switch_brightness(mgr_and_proto):
    mgr, proto = mgr_and_proto
    ok = await mgr.set_switch("mock:1", "brightness", 200)
    assert ok is True
    assert mgr.lamps["mock:1"].switches["brightness"].value == 200


@pytest.mark.asyncio
async def test_set_switch_color(mgr_and_proto):
    mgr, _ = mgr_and_proto
    ok = await mgr.set_switch("mock:1", "color", [128, 0, 255])
    assert ok is True
    assert mgr.lamps["mock:1"].switches["color"].value == [128, 0, 255]


@pytest.mark.asyncio
async def test_set_switch_nonexistent_lamp(mgr_and_proto):
    mgr, _ = mgr_and_proto
    ok = await mgr.set_switch("nonexistent", "power", True)
    assert ok is False


@pytest.mark.asyncio
async def test_set_switch_nonexistent_switch(mgr_and_proto):
    mgr, _ = mgr_and_proto
    ok = await mgr.set_switch("mock:1", "nonexistent_switch", 42)
    assert ok is False


@pytest.mark.asyncio
async def test_toggle_power(mgr_and_proto):
    mgr, _ = mgr_and_proto
    assert mgr.lamps["mock:1"].switches["power"].value is False

    ok = await mgr.toggle_power("mock:1")
    assert ok is True
    assert mgr.lamps["mock:1"].switches["power"].value is True

    ok = await mgr.toggle_power("mock:1")
    assert ok is True
    assert mgr.lamps["mock:1"].switches["power"].value is False


@pytest.mark.asyncio
async def test_set_switch_failure(mgr_and_proto):
    mgr, proto = mgr_and_proto
    proto.set_result = False
    ok = await mgr.set_switch("mock:1", "power", True)
    assert ok is False


@pytest.mark.asyncio
async def test_event_history(mgr_and_proto):
    mgr, _ = mgr_and_proto
    await mgr.set_switch("mock:1", "power", True)
    await mgr.set_switch("mock:1", "brightness", 50)

    assert len(mgr.history) == 2
    assert mgr.history[0].switch_name == "power"
    assert mgr.history[0].new_value is True
    assert mgr.history[1].switch_name == "brightness"
    assert mgr.history[1].new_value == 50


def test_summary(mgr_and_proto):
    mgr, _ = mgr_and_proto
    s = mgr.summary()
    assert s["total_lamps"] == 1
    assert s["connected_lamps"] == 1
    assert s["total_switches"] == 4


def test_get_all_switches(mgr_and_proto):
    mgr, _ = mgr_and_proto
    all_sw = mgr.get_all_switches()
    assert "mock:1" in all_sw
    assert "power" in all_sw["mock:1"]
    assert "brightness" in all_sw["mock:1"]


def test_register_all():
    proto = MockProtocol()
    mgr = SwitchManager([proto])

    lamp1 = _make_connected_lamp()
    lamp2 = Lamp(id="mock:2", name="Disconnected", ip="10.0.0.2", port=80, protocol="mock")
    lamp2.connected = False

    mgr.register_all([lamp1, lamp2])
    assert len(mgr.lamps) == 1  # only connected lamp registered


def test_save_state(mgr_and_proto, tmp_path):
    mgr, _ = mgr_and_proto
    out = tmp_path / "state.json"
    mgr.save_state(out)
    assert out.exists()

    import json
    data = json.loads(out.read_text())
    assert "mock:1" in data
    assert "switches" in data["mock:1"]
    assert "power" in data["mock:1"]["switches"]
