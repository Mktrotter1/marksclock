"""WLED protocol adapter - mDNS discovery, REST/JSON API control."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
import asyncio

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)

WLED_MDNS_TYPE = "_wled._tcp.local."
WLED_HTTP_TYPE = "_http._tcp.local."


class WLEDProtocol(LampProtocol):
    name = "wled"

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session

    async def discover(self, timeout: float = 5.0) -> list[Lamp]:
        lamps: list[Lamp] = []
        found: dict[str, dict[str, Any]] = {}
        loop = asyncio.get_event_loop()
        event = asyncio.Event()

        def on_service_state_change(
            *, zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
        ) -> None:
            if state_change == ServiceStateChange.Added:
                info = zeroconf.get_service_info(service_type, name)
                if info and info.parsed_addresses():
                    ip = info.parsed_addresses()[0]
                    found[name] = {
                        "ip": ip,
                        "port": info.port or 80,
                        "name": info.server.rstrip(".") if info.server else name,
                        "properties": {
                            k.decode(): v.decode() if isinstance(v, bytes) else v
                            for k, v in (info.properties or {}).items()
                        },
                    }

        zc = Zeroconf()
        try:
            ServiceBrowser(zc, WLED_MDNS_TYPE, handlers=[on_service_state_change])
            await asyncio.sleep(timeout)
        finally:
            zc.close()

        for svc_name, info in found.items():
            lamp = Lamp(
                id=f"wled:{info['ip']}",
                name=info["properties"].get("fn", info["name"]),
                ip=info["ip"],
                port=info["port"],
                protocol=self.name,
                model=info["properties"].get("md", ""),
                firmware=info["properties"].get("ver", ""),
                mac=info["properties"].get("mac", ""),
                raw_info=info,
            )
            lamps.append(lamp)

        return lamps

    async def connect(self, lamp: Lamp) -> bool:
        session = await self._get_session()
        try:
            async with session.get(f"http://{lamp.ip}:{lamp.port}/json/state") as resp:
                if resp.status != 200:
                    return False
                state = await resp.json()

            async with session.get(f"http://{lamp.ip}:{lamp.port}/json/info") as resp:
                info = await resp.json() if resp.status == 200 else {}

            async with session.get(f"http://{lamp.ip}:{lamp.port}/json/effects") as resp:
                effects = await resp.json() if resp.status == 200 else []

            async with session.get(f"http://{lamp.ip}:{lamp.port}/json/palettes") as resp:
                palettes = await resp.json() if resp.status == 200 else []

            lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=state.get("on", False)))
            lamp.add_switch(Switch("brightness", SwitchType.RANGE, value=state.get("bri", 0),
                                   min_val=0, max_val=255))

            seg = state.get("seg", [{}])[0] if state.get("seg") else {}
            color = seg.get("col", [[0, 0, 0]])[0] if seg.get("col") else [0, 0, 0]
            lamp.add_switch(Switch("color", SwitchType.COLOR, value=color))

            fx = seg.get("fx", 0)
            lamp.add_switch(Switch("effect", SwitchType.SELECT, value=fx,
                                   options=[str(e) for e in effects] if isinstance(effects, list) else []))

            lamp.add_switch(Switch("effect_speed", SwitchType.RANGE, value=seg.get("sx", 128),
                                   min_val=0, max_val=255))
            lamp.add_switch(Switch("effect_intensity", SwitchType.RANGE, value=seg.get("ix", 128),
                                   min_val=0, max_val=255))

            pal = seg.get("pal", 0)
            lamp.add_switch(Switch("palette", SwitchType.SELECT, value=pal,
                                   options=[str(p) for p in palettes] if isinstance(palettes, list) else []))

            lamp.add_switch(Switch("transition", SwitchType.RANGE, value=state.get("transition", 7),
                                   min_val=0, max_val=255, unit="x100ms"))

            lamp.firmware = info.get("ver", lamp.firmware)
            lamp.model = info.get("arch", lamp.model)
            lamp.mac = info.get("mac", lamp.mac)
            lamp.connected = True
            return True

        except Exception as e:
            logger.error("WLED connect failed for %s: %s", lamp.ip, e)
            return False

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        session = await self._get_session()
        payload: dict[str, Any] = {}

        if switch_name == "power":
            payload = {"on": bool(value)}
        elif switch_name == "brightness":
            payload = {"bri": int(value)}
        elif switch_name == "color":
            payload = {"seg": [{"col": [list(value)]}]}
        elif switch_name == "effect":
            payload = {"seg": [{"fx": int(value)}]}
        elif switch_name == "effect_speed":
            payload = {"seg": [{"sx": int(value)}]}
        elif switch_name == "effect_intensity":
            payload = {"seg": [{"ix": int(value)}]}
        elif switch_name == "palette":
            payload = {"seg": [{"pal": int(value)}]}
        elif switch_name == "transition":
            payload = {"transition": int(value)}
        else:
            return False

        try:
            async with session.post(f"http://{lamp.ip}:{lamp.port}/json/state", json=payload) as resp:
                ok = resp.status == 200
                if ok and switch_name in lamp.switches:
                    lamp.switches[switch_name].value = value
                return ok
        except Exception as e:
            logger.error("WLED set_switch failed: %s", e)
            return False

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        session = await self._get_session()
        try:
            async with session.get(f"http://{lamp.ip}:{lamp.port}/json/state") as resp:
                return await resp.json()
        except Exception:
            return {}

    async def disconnect(self, lamp: Lamp) -> None:
        lamp.connected = False
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
