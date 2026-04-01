"""Switch manager - auto-spawns and manages switches for discovered lamps."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)

STATE_FILE = Path("markslamp_state.json")


@dataclass
class SwitchEvent:
    timestamp: str
    lamp_id: str
    switch_name: str
    old_value: Any
    new_value: Any
    success: bool


class SwitchManager:
    """Manages switches for all connected lamps."""

    def __init__(self, protocols: list[LampProtocol]) -> None:
        self._proto_map: dict[str, LampProtocol] = {p.name: p for p in protocols}
        self.lamps: dict[str, Lamp] = {}
        self.history: list[SwitchEvent] = []

    def register_lamp(self, lamp: Lamp) -> None:
        """Register a connected lamp and its switches."""
        self.lamps[lamp.id] = lamp
        logger.info(
            "Registered lamp %s with %d switches: %s",
            lamp.display_name,
            len(lamp.switches),
            ", ".join(lamp.switches.keys()),
        )

    def register_all(self, lamps: list[Lamp]) -> None:
        for lamp in lamps:
            if lamp.connected:
                self.register_lamp(lamp)

    def get_lamp(self, lamp_id: str) -> Lamp | None:
        return self.lamps.get(lamp_id)

    def get_switch(self, lamp_id: str, switch_name: str) -> Switch | None:
        lamp = self.lamps.get(lamp_id)
        if lamp:
            return lamp.switches.get(switch_name)
        return None

    async def set_switch(self, lamp_id: str, switch_name: str, value: Any) -> bool:
        """Set a switch value and record the event."""
        lamp = self.lamps.get(lamp_id)
        if not lamp:
            logger.warning("Lamp %s not found", lamp_id)
            return False

        sw = lamp.switches.get(switch_name)
        if not sw:
            logger.warning("Switch %s not found on %s", switch_name, lamp.display_name)
            return False

        proto = self._proto_map.get(lamp.protocol)
        if not proto:
            logger.error("No protocol adapter for %s", lamp.protocol)
            return False

        old_value = sw.value
        success = await proto.set_switch(lamp, switch_name, value)

        event = SwitchEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            lamp_id=lamp_id,
            switch_name=switch_name,
            old_value=old_value,
            new_value=value,
            success=success,
        )
        self.history.append(event)
        logger.info(
            "%s %s.%s: %s -> %s",
            "SET" if success else "FAIL",
            lamp.display_name,
            switch_name,
            old_value,
            value,
        )

        return success

    async def toggle_power(self, lamp_id: str) -> bool:
        """Toggle the power switch of a lamp."""
        sw = self.get_switch(lamp_id, "power")
        if sw:
            return await self.set_switch(lamp_id, "power", not sw.value)
        return False

    async def refresh_state(self, lamp_id: str) -> dict[str, Any]:
        """Refresh the state of a lamp from the device."""
        lamp = self.lamps.get(lamp_id)
        if not lamp:
            return {}

        proto = self._proto_map.get(lamp.protocol)
        if not proto:
            return {}

        return await proto.get_state(lamp)

    def get_all_switches(self) -> dict[str, dict[str, Switch]]:
        """Get all switches grouped by lamp."""
        return {
            lamp_id: dict(lamp.switches)
            for lamp_id, lamp in self.lamps.items()
            if lamp.connected
        }

    def save_state(self, path: Path = STATE_FILE) -> None:
        """Persist current state to JSON."""
        state = {}
        for lamp_id, lamp in self.lamps.items():
            state[lamp_id] = {
                "name": lamp.name,
                "ip": lamp.ip,
                "protocol": lamp.protocol,
                "switches": {
                    name: {"type": sw.switch_type.value, "value": sw.value}
                    for name, sw in lamp.switches.items()
                },
            }
        path.write_text(json.dumps(state, indent=2, default=str))
        logger.info("State saved to %s", path)

    def summary(self) -> dict[str, Any]:
        """Return a summary of all managed lamps and switches."""
        return {
            "total_lamps": len(self.lamps),
            "connected_lamps": sum(1 for l in self.lamps.values() if l.connected),
            "total_switches": sum(len(l.switches) for l in self.lamps.values()),
            "lamps": {
                lid: {
                    "name": l.display_name,
                    "protocol": l.protocol,
                    "ip": l.ip,
                    "switches": {n: s.display for n, s in l.switches.items()},
                }
                for lid, l in self.lamps.items()
            },
        }
