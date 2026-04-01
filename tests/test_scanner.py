"""Tests for the scanner engine."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol
from markslamp.scanner import Scanner


class FakeProtocol(LampProtocol):
    """Fake protocol for testing."""

    name = "fake"

    def __init__(self, lamps: list[Lamp] | None = None, connect_ok: bool = True):
        self._lamps = lamps or []
        self._connect_ok = connect_ok

    async def discover(self, timeout: float = 5.0) -> list[Lamp]:
        return self._lamps

    async def connect(self, lamp: Lamp) -> bool:
        if self._connect_ok:
            lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=True))
            lamp.add_switch(Switch("brightness", SwitchType.RANGE, value=128, min_val=0, max_val=255))
            lamp.connected = True
        return self._connect_ok

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        if switch_name in lamp.switches:
            lamp.switches[switch_name].value = value
            return True
        return False

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        return {n: s.value for n, s in lamp.switches.items()}


class FailingProtocol(LampProtocol):
    name = "failing"

    async def discover(self, timeout: float = 5.0) -> list[Lamp]:
        raise ConnectionError("Network unreachable")

    async def connect(self, lamp: Lamp) -> bool:
        return False

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        return False

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        return {}


def _make_lamp(ip: str = "192.168.1.100", name: str = "Test Lamp") -> Lamp:
    return Lamp(id=f"fake:{ip}", name=name, ip=ip, port=80, protocol="fake")


@pytest.mark.asyncio
async def test_scan_finds_lamps():
    lamp = _make_lamp()
    proto = FakeProtocol(lamps=[lamp])
    scanner = Scanner([proto], timeout=1.0)

    found = await scanner.scan()
    assert len(found) == 1
    assert "fake:192.168.1.100" in found


@pytest.mark.asyncio
async def test_scan_deduplicates():
    lamp1 = _make_lamp("10.0.0.1", "Lamp A")
    lamp2 = _make_lamp("10.0.0.1", "Lamp A duplicate")
    lamp2.id = lamp1.id  # same ID

    proto = FakeProtocol(lamps=[lamp1, lamp2])
    scanner = Scanner([proto], timeout=1.0)
    found = await scanner.scan()
    assert len(found) == 1


@pytest.mark.asyncio
async def test_scan_multiple_protocols():
    lamp1 = _make_lamp("10.0.0.1", "Lamp 1")
    lamp2 = _make_lamp("10.0.0.2", "Lamp 2")
    lamp2.id = "fake:10.0.0.2"

    proto1 = FakeProtocol(lamps=[lamp1])
    proto2 = FakeProtocol(lamps=[lamp2])
    scanner = Scanner([proto1, proto2], timeout=1.0)

    found = await scanner.scan()
    assert len(found) == 2


@pytest.mark.asyncio
async def test_scan_handles_protocol_failure():
    lamp = _make_lamp()
    good = FakeProtocol(lamps=[lamp])
    bad = FailingProtocol()

    scanner = Scanner([good, bad], timeout=1.0)
    found = await scanner.scan()
    assert len(found) == 1


@pytest.mark.asyncio
async def test_connect_all():
    lamp = _make_lamp()
    proto = FakeProtocol(lamps=[lamp])
    scanner = Scanner([proto], timeout=1.0)

    await scanner.scan()
    connected = await scanner.connect_all()

    assert len(connected) == 1
    assert connected[0].connected is True
    assert "power" in connected[0].switches
    assert "brightness" in connected[0].switches


@pytest.mark.asyncio
async def test_connect_all_with_failure():
    lamp = _make_lamp()
    proto = FakeProtocol(lamps=[lamp], connect_ok=False)
    scanner = Scanner([proto], timeout=1.0)

    await scanner.scan()
    connected = await scanner.connect_all()
    assert len(connected) == 0


@pytest.mark.asyncio
async def test_scan_empty_network():
    proto = FakeProtocol(lamps=[])
    scanner = Scanner([proto], timeout=1.0)
    found = await scanner.scan()
    assert len(found) == 0
