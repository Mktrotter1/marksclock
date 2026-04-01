"""Philips Hue protocol adapter - mDNS/SSDP discovery, REST API via bridge."""

from __future__ import annotations

import logging
import os
from typing import Any

from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
import aiohttp
import asyncio

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)


class HueProtocol(LampProtocol):
    name = "hue"

    def __init__(self) -> None:
        self._bridge_ip: str = os.environ.get("HUE_BRIDGE_IP", "")
        self._username: str = ""
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session

    async def _find_bridge(self, timeout: float) -> str | None:
        if self._bridge_ip:
            return self._bridge_ip

        found_ip: list[str] = []

        def on_service(
            zc: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
        ) -> None:
            if state_change == ServiceStateChange.Added:
                info = zc.get_service_info(service_type, name)
                if info and info.parsed_addresses() and "hue" in name.lower():
                    found_ip.append(info.parsed_addresses()[0])

        zc = Zeroconf()
        try:
            ServiceBrowser(zc, "_hue._tcp.local.", handlers=[on_service])
            await asyncio.sleep(timeout)
        finally:
            zc.close()

        return found_ip[0] if found_ip else None

    async def discover(self, timeout: float = 5.0) -> list[Lamp]:
        bridge_ip = await self._find_bridge(timeout)
        if not bridge_ip:
            logger.debug("No Hue bridge found")
            return []

        self._bridge_ip = bridge_ip

        try:
            from phue import Bridge
            b = Bridge(bridge_ip)
            b.connect()
            self._username = b.username
        except Exception as e:
            logger.warning("Hue bridge auth needed (press link button): %s", e)
            return []

        lamps: list[Lamp] = []
        session = await self._get_session()

        try:
            async with session.get(f"http://{bridge_ip}/api/{self._username}/lights") as resp:
                if resp.status != 200:
                    return []
                lights = await resp.json()

            for light_id, info in lights.items():
                lamp = Lamp(
                    id=f"hue:{bridge_ip}:{light_id}",
                    name=info.get("name", f"Hue Light {light_id}"),
                    ip=bridge_ip,
                    port=80,
                    protocol=self.name,
                    model=info.get("modelid", ""),
                    firmware=info.get("swversion", ""),
                    mac=info.get("uniqueid", ""),
                    raw_info={"light_id": light_id, "info": info},
                )
                lamps.append(lamp)
        except Exception as e:
            logger.error("Hue discovery failed: %s", e)

        return lamps

    async def connect(self, lamp: Lamp) -> bool:
        light_id = lamp.raw_info.get("light_id")
        info = lamp.raw_info.get("info", {})
        state = info.get("state", {})

        lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=state.get("on", False)))

        if "bri" in state:
            lamp.add_switch(Switch("brightness", SwitchType.RANGE,
                                   value=state["bri"], min_val=1, max_val=254))

        if "ct" in state:
            lamp.add_switch(Switch("color_temp", SwitchType.RANGE,
                                   value=state["ct"], min_val=153, max_val=500))

        if "hue" in state:
            lamp.add_switch(Switch("hue", SwitchType.RANGE,
                                   value=state["hue"], min_val=0, max_val=65535))
            lamp.add_switch(Switch("saturation", SwitchType.RANGE,
                                   value=state.get("sat", 0), min_val=0, max_val=254))

        if "xy" in state:
            lamp.add_switch(Switch("color", SwitchType.COLOR, value=state["xy"]))

        if "effect" in state:
            lamp.add_switch(Switch("effect", SwitchType.SELECT, value=state["effect"],
                                   options=["none", "colorloop"]))

        if "alert" in state:
            lamp.add_switch(Switch("alert", SwitchType.SELECT, value=state["alert"],
                                   options=["none", "select", "lselect"]))

        lamp.connected = True
        return True

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        light_id = lamp.raw_info.get("light_id")
        if not light_id or not self._username:
            return False

        session = await self._get_session()
        payload: dict[str, Any] = {}

        if switch_name == "power":
            payload = {"on": bool(value)}
        elif switch_name == "brightness":
            payload = {"bri": int(value)}
        elif switch_name == "color_temp":
            payload = {"ct": int(value)}
        elif switch_name == "hue":
            payload = {"hue": int(value)}
        elif switch_name == "saturation":
            payload = {"sat": int(value)}
        elif switch_name == "color":
            if isinstance(value, (list, tuple)) and len(value) == 2:
                payload = {"xy": list(value)}
        elif switch_name == "effect":
            payload = {"effect": str(value)}
        elif switch_name == "alert":
            payload = {"alert": str(value)}
        else:
            return False

        try:
            url = f"http://{self._bridge_ip}/api/{self._username}/lights/{light_id}/state"
            async with session.put(url, json=payload) as resp:
                ok = resp.status == 200
                if ok and switch_name in lamp.switches:
                    lamp.switches[switch_name].value = value
                return ok
        except Exception as e:
            logger.error("Hue set_switch failed: %s", e)
            return False

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        light_id = lamp.raw_info.get("light_id")
        if not light_id or not self._username:
            return {}

        session = await self._get_session()
        try:
            url = f"http://{self._bridge_ip}/api/{self._username}/lights/{light_id}"
            async with session.get(url) as resp:
                data = await resp.json()
                return data.get("state", {})
        except Exception:
            return {}

    async def disconnect(self, lamp: Lamp) -> None:
        lamp.connected = False
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
