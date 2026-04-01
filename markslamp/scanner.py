"""Network scanner - discovers lamps across all protocols."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from markslamp.models import Lamp

if TYPE_CHECKING:
    from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)


class Scanner:
    """Discovers lamps by running all protocol adapters concurrently."""

    def __init__(self, protocols: list[LampProtocol], timeout: float = 5.0) -> None:
        self.protocols = protocols
        self.timeout = timeout
        self.lamps: dict[str, Lamp] = {}

    async def scan(self) -> dict[str, Lamp]:
        """Run discovery across all protocols concurrently."""
        logger.info("Starting scan with %d protocols (timeout=%.1fs)", len(self.protocols), self.timeout)

        tasks = [self._run_protocol(proto) for proto in self.protocols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for proto, result in zip(self.protocols, results):
            if isinstance(result, Exception):
                logger.warning("Protocol %s discovery failed: %s", proto.name, result)
            elif isinstance(result, list):
                for lamp in result:
                    key = lamp.id or f"{lamp.protocol}:{lamp.ip}:{lamp.port}"
                    if key not in self.lamps:
                        self.lamps[key] = lamp
                        logger.info("Found: %s (%s) at %s", lamp.display_name, lamp.protocol, lamp.ip)

        logger.info("Scan complete: %d lamps found", len(self.lamps))
        return self.lamps

    async def _run_protocol(self, proto: LampProtocol) -> list[Lamp]:
        """Run a single protocol's discovery with timeout."""
        try:
            return await asyncio.wait_for(proto.discover(self.timeout), timeout=self.timeout + 2)
        except asyncio.TimeoutError:
            logger.warning("Protocol %s timed out", proto.name)
            return []
        except ImportError as e:
            logger.debug("Protocol %s unavailable (missing dependency): %s", proto.name, e)
            return []

    async def connect_all(self) -> list[Lamp]:
        """Connect to all discovered lamps and populate their switches."""
        proto_map = {p.name: p for p in self.protocols}
        tasks = []

        for lamp in self.lamps.values():
            proto = proto_map.get(lamp.protocol)
            if proto:
                tasks.append(self._connect_lamp(proto, lamp))

        await asyncio.gather(*tasks, return_exceptions=True)
        return [l for l in self.lamps.values() if l.connected]

    async def _connect_lamp(self, proto: LampProtocol, lamp: Lamp) -> None:
        """Connect to a single lamp."""
        try:
            ok = await asyncio.wait_for(proto.connect(lamp), timeout=10)
            if ok:
                logger.info("Connected: %s (%d switches)", lamp.display_name, len(lamp.switches))
            else:
                logger.warning("Failed to connect: %s", lamp.display_name)
        except Exception as e:
            logger.warning("Error connecting %s: %s", lamp.display_name, e)
