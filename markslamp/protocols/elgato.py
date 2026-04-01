"""Elgato Key Light protocol adapter - mDNS discovery, REST JSON control."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
import asyncio

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)

ELGATO_MDNS_TYPE = "_elg._tcp.local."


class ElgatoProtocol(LampProtocol):
    name = "elgato"

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session

    async def discover(self, timeout: float = 5.0) -> list[Lamp]:
        lamps: list[Lamp] = []
        found: dict[str, dict[str, Any]] = {}

        def on_service(
            zc: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
        ) -> None:
            if state_change == ServiceStateChange.Added:
                info = zc.get_service_info(service_type, name)
                if info and info.parsed_addresses():
                    props = {
                        k.decode(): v.decode() if isinstance(v, bytes) else v
                        for k, v in (info.properties or {}).items()
                    }
                    found[name] = {
                        "ip": info.parsed_addresses()[0],
                        "port": info.port or 9123,
                        "name": info.server.rstrip(".") if info.server else name,
                        "properties": props,
                    }

        zc = Zeroconf()
        try:
            ServiceBrowser(zc, ELGATO_MDNS_TYPE, handlers=[on_service])
            await asyncio.sleep(timeout)
        finally:
            zc.close()

        session = await self._get_session()
        for svc_name, info in found.items():
            try:
                url = f"http://{info['ip']}:{info['port']}/elgato/accessory-info"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        acc_info = await resp.json()
                        lamp = Lamp(
                            id=f"elgato:{info['ip']}",
                            name=acc_info.get("displayName", info["name"]),
                            ip=info["ip"],
                            port=info["port"],
                            protocol=self.name,
                            model=acc_info.get("productName", ""),
                            firmware=acc_info.get("firmwareVersion", ""),
                            mac=acc_info.get("macAddress", ""),
                            raw_info=acc_info,
                        )
                        lamps.append(lamp)
            except Exception as e:
                logger.debug("Elgato probe failed for %s: %s", info["ip"], e)

        return lamps

    async def connect(self, lamp: Lamp) -> bool:
        session = await self._get_session()
        try:
            url = f"http://{lamp.ip}:{lamp.port}/elgato/lights"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()

            lights = data.get("lights", [])
            if not lights:
                return False

            light = lights[0]
            lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=light.get("on", 0) == 1))
            lamp.add_switch(Switch("brightness", SwitchType.RANGE,
                                   value=light.get("brightness", 50),
                                   min_val=3, max_val=100, unit="%"))
            lamp.add_switch(Switch("color_temp", SwitchType.RANGE,
                                   value=light.get("temperature", 200),
                                   min_val=143, max_val=344))

            lamp.connected = True
            return True
        except Exception as e:
            logger.error("Elgato connect failed: %s", e)
            return False

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        session = await self._get_session()

        # Get current state first
        try:
            url = f"http://{lamp.ip}:{lamp.port}/elgato/lights"
            async with session.get(url) as resp:
                data = await resp.json()
            light = data.get("lights", [{}])[0]
        except Exception:
            light = {}

        if switch_name == "power":
            light["on"] = 1 if value else 0
        elif switch_name == "brightness":
            light["brightness"] = int(value)
        elif switch_name == "color_temp":
            light["temperature"] = int(value)
        else:
            return False

        try:
            payload = {"numberOfLights": 1, "lights": [light]}
            async with session.put(url, json=payload) as resp:
                ok = resp.status == 200
                if ok and switch_name in lamp.switches:
                    lamp.switches[switch_name].value = value
                return ok
        except Exception as e:
            logger.error("Elgato set_switch failed: %s", e)
            return False

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        session = await self._get_session()
        try:
            url = f"http://{lamp.ip}:{lamp.port}/elgato/lights"
            async with session.get(url) as resp:
                return await resp.json()
        except Exception:
            return {}

    async def disconnect(self, lamp: Lamp) -> None:
        lamp.connected = False
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
