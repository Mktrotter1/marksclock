"""Shelly protocol adapter - mDNS discovery, REST API control."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
import asyncio

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)


class ShellyProtocol(LampProtocol):
    name = "shelly"

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
                if info and info.parsed_addresses() and "shelly" in name.lower():
                    found[name] = {
                        "ip": info.parsed_addresses()[0],
                        "port": info.port or 80,
                        "name": info.server.rstrip(".") if info.server else name,
                    }

        zc = Zeroconf()
        try:
            ServiceBrowser(zc, "_http._tcp.local.", handlers=[on_service])
            await asyncio.sleep(timeout)
        finally:
            zc.close()

        session = await self._get_session()
        for svc_name, info in found.items():
            ip = info["ip"]
            # Try Gen2 first, then Gen1
            gen2 = await self._probe_gen2(session, ip)
            if gen2:
                lamps.append(gen2)
                continue
            gen1 = await self._probe_gen1(session, ip, info)
            if gen1:
                lamps.append(gen1)

        return lamps

    async def _probe_gen2(self, session: aiohttp.ClientSession, ip: str) -> Lamp | None:
        try:
            async with session.post(f"http://{ip}/rpc/Shelly.GetDeviceInfo", json={"id": 1}) as resp:
                if resp.status != 200:
                    return None
                info = await resp.json()
                if info.get("app") and "light" not in info.get("app", "").lower():
                    return None
                return Lamp(
                    id=f"shelly:{info.get('id', ip)}",
                    name=info.get("name", info.get("id", ip)),
                    ip=ip,
                    port=80,
                    protocol=self.name,
                    model=info.get("model", info.get("app", "")),
                    firmware=info.get("ver", ""),
                    mac=info.get("mac", ""),
                    raw_info={"gen": 2, "info": info},
                )
        except Exception:
            return None

    async def _probe_gen1(self, session: aiohttp.ClientSession, ip: str,
                          svc_info: dict) -> Lamp | None:
        try:
            async with session.get(f"http://{ip}/shelly") as resp:
                if resp.status != 200:
                    return None
                info = await resp.json()
                if not info.get("type", "").startswith("SH"):
                    return None
                return Lamp(
                    id=f"shelly:{info.get('mac', ip)}",
                    name=svc_info.get("name", ip),
                    ip=ip,
                    port=80,
                    protocol=self.name,
                    model=info.get("type", ""),
                    firmware=info.get("fw", ""),
                    mac=info.get("mac", ""),
                    raw_info={"gen": 1, "info": info},
                )
        except Exception:
            return None

    async def connect(self, lamp: Lamp) -> bool:
        gen = lamp.raw_info.get("gen", 1)
        session = await self._get_session()

        try:
            if gen == 2:
                return await self._connect_gen2(session, lamp)
            else:
                return await self._connect_gen1(session, lamp)
        except Exception as e:
            logger.error("Shelly connect failed: %s", e)
            return False

    async def _connect_gen2(self, session: aiohttp.ClientSession, lamp: Lamp) -> bool:
        async with session.post(f"http://{lamp.ip}/rpc/Light.GetStatus",
                               json={"id": 0}) as resp:
            if resp.status != 200:
                return False
            state = await resp.json()

        lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=state.get("output", False)))
        if "brightness" in state:
            lamp.add_switch(Switch("brightness", SwitchType.RANGE,
                                   value=state["brightness"], min_val=0, max_val=100, unit="%"))
        lamp.connected = True
        return True

    async def _connect_gen1(self, session: aiohttp.ClientSession, lamp: Lamp) -> bool:
        async with session.get(f"http://{lamp.ip}/light/0") as resp:
            if resp.status != 200:
                async with session.get(f"http://{lamp.ip}/relay/0") as r2:
                    if r2.status != 200:
                        return False
                    state = await r2.json()
                    lamp.add_switch(Switch("power", SwitchType.TOGGLE,
                                           value=state.get("ison", False)))
                    lamp.connected = True
                    return True

            state = await resp.json()

        lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=state.get("ison", False)))
        if "brightness" in state:
            lamp.add_switch(Switch("brightness", SwitchType.RANGE,
                                   value=state["brightness"], min_val=0, max_val=100, unit="%"))
        if "red" in state:
            lamp.add_switch(Switch("color", SwitchType.COLOR,
                                   value=[state.get("red", 0), state.get("green", 0),
                                          state.get("blue", 0)]))
        if "temp" in state:
            lamp.add_switch(Switch("color_temp", SwitchType.RANGE,
                                   value=state["temp"], min_val=3000, max_val=6500, unit="K"))
        if "effect" in state:
            lamp.add_switch(Switch("effect", SwitchType.SELECT,
                                   value=str(state["effect"]),
                                   options=["0", "1", "2", "3"]))

        lamp.connected = True
        return True

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        gen = lamp.raw_info.get("gen", 1)
        session = await self._get_session()

        try:
            if gen == 2:
                return await self._set_gen2(session, lamp, switch_name, value)
            else:
                return await self._set_gen1(session, lamp, switch_name, value)
        except Exception as e:
            logger.error("Shelly set_switch failed: %s", e)
            return False

    async def _set_gen2(self, session: aiohttp.ClientSession, lamp: Lamp,
                        name: str, value: Any) -> bool:
        payload: dict[str, Any] = {"id": 0}
        if name == "power":
            payload["on"] = bool(value)
        elif name == "brightness":
            payload["brightness"] = int(value)
        else:
            return False

        async with session.post(f"http://{lamp.ip}/rpc/Light.Set", json=payload) as resp:
            ok = resp.status == 200
            if ok and name in lamp.switches:
                lamp.switches[name].value = value
            return ok

    async def _set_gen1(self, session: aiohttp.ClientSession, lamp: Lamp,
                        name: str, value: Any) -> bool:
        params: dict[str, str] = {}
        if name == "power":
            params["turn"] = "on" if value else "off"
        elif name == "brightness":
            params["brightness"] = str(int(value))
        elif name == "color":
            if isinstance(value, (list, tuple)) and len(value) == 3:
                params["red"] = str(value[0])
                params["green"] = str(value[1])
                params["blue"] = str(value[2])
        elif name == "color_temp":
            params["temp"] = str(int(value))
        else:
            return False

        async with session.get(f"http://{lamp.ip}/light/0", params=params) as resp:
            ok = resp.status == 200
            if ok and name in lamp.switches:
                lamp.switches[name].value = value
            return ok

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        return {n: s.value for n, s in lamp.switches.items()}

    async def disconnect(self, lamp: Lamp) -> None:
        lamp.connected = False
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
