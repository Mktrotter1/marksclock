"""ESPHome protocol adapter - mDNS discovery, native API control."""

from __future__ import annotations

import logging
from typing import Any

from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
import asyncio

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)

ESPHOME_MDNS_TYPE = "_esphomelib._tcp.local."


class ESPHomeProtocol(LampProtocol):
    name = "esphome"

    def __init__(self) -> None:
        self._clients: dict[str, Any] = {}

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
                        "port": info.port or 6053,
                        "name": info.server.rstrip(".") if info.server else name,
                        "properties": props,
                    }

        zc = Zeroconf()
        try:
            ServiceBrowser(zc, ESPHOME_MDNS_TYPE, handlers=[on_service])
            await asyncio.sleep(timeout)
        finally:
            zc.close()

        for svc_name, info in found.items():
            lamp = Lamp(
                id=f"esphome:{info['ip']}",
                name=info["properties"].get("friendly_name", info["name"]),
                ip=info["ip"],
                port=info["port"],
                protocol=self.name,
                model=info["properties"].get("project_name", ""),
                firmware=info["properties"].get("project_version", ""),
                mac=info["properties"].get("mac", ""),
                raw_info=info,
            )
            lamps.append(lamp)

        return lamps

    async def connect(self, lamp: Lamp) -> bool:
        try:
            from aioesphomeapi import APIClient, LightInfo, LightState
        except ImportError:
            logger.debug("aioesphomeapi not installed")
            return False

        try:
            client = APIClient(lamp.ip, lamp.port, password="")
            await client.connect(login=True)

            entities, services = await client.list_entities_services()
            light_entities = [e for e in entities if isinstance(e, LightInfo)]

            if not light_entities:
                logger.info("ESPHome device %s has no light entities", lamp.ip)
                await client.disconnect()
                return False

            for light in light_entities:
                prefix = f"{light.name}:" if len(light_entities) > 1 else ""
                lamp.add_switch(Switch(f"{prefix}power", SwitchType.TOGGLE, value=False))

                if light.supported_color_modes:
                    lamp.add_switch(Switch(f"{prefix}brightness", SwitchType.RANGE,
                                           value=0, min_val=0, max_val=255))
                    lamp.add_switch(Switch(f"{prefix}color", SwitchType.COLOR,
                                           value=[0, 0, 0]))
                    lamp.add_switch(Switch(f"{prefix}color_temp", SwitchType.RANGE,
                                           value=370, min_val=153, max_val=500))

                if light.effects:
                    lamp.add_switch(Switch(f"{prefix}effect", SwitchType.SELECT,
                                           value=light.effects[0] if light.effects else "",
                                           options=list(light.effects)))

            self._clients[lamp.id] = client
            lamp.raw_info["_light_entities"] = light_entities
            lamp.connected = True
            return True
        except Exception as e:
            logger.error("ESPHome connect failed: %s", e)
            return False

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        client = self._clients.get(lamp.id)
        if not client:
            return False

        light_entities = lamp.raw_info.get("_light_entities", [])
        if not light_entities:
            return False

        # Find the right light entity (first one, or match prefix)
        light = light_entities[0]
        key = light.key

        try:
            if "power" in switch_name:
                await client.light_command(key, state=bool(value))
            elif "brightness" in switch_name:
                await client.light_command(key, brightness=int(value) / 255.0)
            elif "color_temp" in switch_name:
                await client.light_command(key, color_temperature=int(value))
            elif "color" in switch_name:
                if isinstance(value, (list, tuple)) and len(value) == 3:
                    await client.light_command(
                        key, rgb=(value[0] / 255.0, value[1] / 255.0, value[2] / 255.0)
                    )
            elif "effect" in switch_name:
                await client.light_command(key, effect=str(value))
            else:
                return False

            if switch_name in lamp.switches:
                lamp.switches[switch_name].value = value
            return True
        except Exception as e:
            logger.error("ESPHome set_switch failed: %s", e)
            return False

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        return {name: sw.value for name, sw in lamp.switches.items()}

    async def disconnect(self, lamp: Lamp) -> None:
        client = self._clients.pop(lamp.id, None)
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
        lamp.connected = False
