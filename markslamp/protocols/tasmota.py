"""Tasmota protocol adapter - mDNS discovery, HTTP command API."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
import asyncio

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)


class TasmotaProtocol(LampProtocol):
    name = "tasmota"

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
            *, zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
        ) -> None:
            if state_change == ServiceStateChange.Added:
                info = zeroconf.get_service_info(service_type, name)
                if info and info.parsed_addresses():
                    props = {
                        k.decode(): v.decode() if isinstance(v, bytes) else v
                        for k, v in (info.properties or {}).items()
                    }
                    # Tasmota devices advertise via _http._tcp with "Tasmota" in their name/properties
                    if "tasmota" in name.lower() or "tasmota" in str(props).lower():
                        found[name] = {
                            "ip": info.parsed_addresses()[0],
                            "port": info.port or 80,
                            "name": info.server.rstrip(".") if info.server else name,
                            "properties": props,
                        }

        zc = Zeroconf()
        try:
            ServiceBrowser(zc, "_http._tcp.local.", handlers=[on_service])
            await asyncio.sleep(timeout)
        finally:
            zc.close()

        # Also try HTTP probing common Tasmota status endpoint
        session = await self._get_session()
        for svc_name, info in found.items():
            try:
                async with session.get(f"http://{info['ip']}/cm?cmnd=Status%200") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        status = data.get("Status", {})
                        lamp = Lamp(
                            id=f"tasmota:{info['ip']}",
                            name=status.get("DeviceName", status.get("FriendlyName", [info["name"]])[0]
                                            if isinstance(status.get("FriendlyName"), list)
                                            else status.get("FriendlyName", info["name"])),
                            ip=info["ip"],
                            port=info["port"],
                            protocol=self.name,
                            model=status.get("Module", ""),
                            firmware=data.get("StatusFWR", {}).get("Version", ""),
                            raw_info=data,
                        )
                        lamps.append(lamp)
            except Exception as e:
                logger.debug("Tasmota probe failed for %s: %s", info["ip"], e)

        return lamps

    async def connect(self, lamp: Lamp) -> bool:
        session = await self._get_session()
        try:
            async with session.get(f"http://{lamp.ip}/cm?cmnd=State") as resp:
                if resp.status != 200:
                    return False
                state = await resp.json()

            power_state = state.get("POWER", state.get("POWER1", "OFF"))
            lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=power_state == "ON"))

            # Check for dimmer capability
            dimmer = state.get("Dimmer")
            if dimmer is not None:
                lamp.add_switch(Switch("brightness", SwitchType.RANGE,
                                       value=int(dimmer), min_val=0, max_val=100, unit="%"))

            ct = state.get("CT")
            if ct is not None:
                lamp.add_switch(Switch("color_temp", SwitchType.RANGE,
                                       value=int(ct), min_val=153, max_val=500))

            color = state.get("Color")
            if color and len(color) >= 6:
                r = int(color[0:2], 16)
                g = int(color[2:4], 16)
                b = int(color[4:6], 16)
                lamp.add_switch(Switch("color", SwitchType.COLOR, value=[r, g, b]))

            scheme = state.get("Scheme")
            if scheme is not None:
                lamp.add_switch(Switch("effect", SwitchType.SELECT, value=str(scheme),
                                       options=["0", "1", "2", "3", "4"]))

            lamp.connected = True
            return True
        except Exception as e:
            logger.error("Tasmota connect failed: %s", e)
            return False

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        session = await self._get_session()
        cmnd = ""

        if switch_name == "power":
            cmnd = f"Power {'ON' if value else 'OFF'}"
        elif switch_name == "brightness":
            cmnd = f"Dimmer {int(value)}"
        elif switch_name == "color_temp":
            cmnd = f"CT {int(value)}"
        elif switch_name == "color":
            if isinstance(value, (list, tuple)) and len(value) == 3:
                cmnd = f"Color {value[0]:02x}{value[1]:02x}{value[2]:02x}"
        elif switch_name == "effect":
            cmnd = f"Scheme {value}"
        else:
            return False

        try:
            async with session.get(f"http://{lamp.ip}/cm?cmnd={cmnd}") as resp:
                ok = resp.status == 200
                if ok and switch_name in lamp.switches:
                    lamp.switches[switch_name].value = value
                return ok
        except Exception as e:
            logger.error("Tasmota set_switch failed: %s", e)
            return False

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        session = await self._get_session()
        try:
            async with session.get(f"http://{lamp.ip}/cm?cmnd=State") as resp:
                return await resp.json()
        except Exception:
            return {}

    async def disconnect(self, lamp: Lamp) -> None:
        lamp.connected = False
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
