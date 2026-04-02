"""Data models for lamp discovery and control."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class SwitchType(enum.Enum):
    TOGGLE = "toggle"       # on/off
    RANGE = "range"         # slider (brightness, color_temp)
    COLOR = "color"         # RGB/HSV picker
    SELECT = "select"       # dropdown (effects, modes)
    BUTTON = "button"       # momentary press (RF bridge, cycle lamp)


@dataclass
class Switch:
    """A controllable variable on a lamp."""

    name: str
    switch_type: SwitchType
    value: Any = None
    min_val: float | None = None
    max_val: float | None = None
    options: list[str] = field(default_factory=list)
    unit: str = ""

    @property
    def display(self) -> str:
        if self.switch_type == SwitchType.TOGGLE:
            return f"{'ON' if self.value else 'OFF'}"
        if self.switch_type == SwitchType.RANGE:
            return f"{self.value}{self.unit}"
        if self.switch_type == SwitchType.COLOR:
            return f"({self.value})"
        if self.switch_type == SwitchType.SELECT:
            return f"{self.value}"
        if self.switch_type == SwitchType.BUTTON:
            return "PRESS"
        return str(self.value)


@dataclass
class Lamp:
    """A discovered smart lamp."""

    id: str
    name: str
    ip: str
    port: int
    protocol: str
    model: str = ""
    firmware: str = ""
    mac: str = ""
    switches: dict[str, Switch] = field(default_factory=dict)
    connected: bool = False
    raw_info: dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return self.name or f"{self.protocol}@{self.ip}"

    def add_switch(self, switch: Switch) -> None:
        self.switches[switch.name] = switch
