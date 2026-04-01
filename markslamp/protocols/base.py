"""Base protocol adapter interface."""

from __future__ import annotations

import abc
import logging
from typing import Any

from markslamp.models import Lamp

logger = logging.getLogger(__name__)


class LampProtocol(abc.ABC):
    """Base class for all lamp protocol adapters.

    Each adapter must implement discovery and control for its protocol.
    """

    name: str = "unknown"

    @abc.abstractmethod
    async def discover(self, timeout: float = 5.0) -> list[Lamp]:
        """Scan the network for lamps using this protocol."""

    @abc.abstractmethod
    async def connect(self, lamp: Lamp) -> bool:
        """Connect to a lamp and populate its switches."""

    @abc.abstractmethod
    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        """Set a switch value on a connected lamp."""

    @abc.abstractmethod
    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        """Get current state of all switches."""

    async def disconnect(self, lamp: Lamp) -> None:
        """Disconnect from a lamp. Override if cleanup is needed."""
        lamp.connected = False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
