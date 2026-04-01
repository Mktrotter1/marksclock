"""LIFX protocol adapter - UDP broadcast discovery and control."""

from __future__ import annotations

import logging
from typing import Any

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)


class LIFXProtocol(LampProtocol):
    name = "lifx"

    def __init__(self) -> None:
        self._lan = None

    async def discover(self, timeout: float = 5.0) -> list[Lamp]:
        try:
            from lifxlan import LifxLAN
        except ImportError:
            logger.debug("lifxlan not installed, skipping LIFX discovery")
            return []

        lamps: list[Lamp] = []
        lan = LifxLAN()
        devices = lan.get_lights()

        for dev in devices:
            try:
                ip = dev.get_ip_addr()
                label = dev.get_label()
                mac = dev.get_mac_addr()
                lamp = Lamp(
                    id=f"lifx:{mac}",
                    name=label,
                    ip=ip,
                    port=56700,
                    protocol=self.name,
                    mac=mac,
                    model=str(dev.get_product()),
                    firmware=str(dev.get_host_firmware_version()),
                )
                lamps.append(lamp)
            except Exception as e:
                logger.debug("LIFX device error: %s", e)

        self._lan = lan
        return lamps

    async def connect(self, lamp: Lamp) -> bool:
        try:
            from lifxlan import Light
        except ImportError:
            return False

        try:
            light = Light(lamp.mac, lamp.ip)
            power = light.get_power()
            color = light.get_color()  # (hue, sat, brightness, kelvin)

            lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=power > 0))
            lamp.add_switch(Switch("hue", SwitchType.RANGE, value=color[0],
                                   min_val=0, max_val=65535))
            lamp.add_switch(Switch("saturation", SwitchType.RANGE, value=color[1],
                                   min_val=0, max_val=65535))
            lamp.add_switch(Switch("brightness", SwitchType.RANGE, value=color[2],
                                   min_val=0, max_val=65535))
            lamp.add_switch(Switch("color_temp", SwitchType.RANGE, value=color[3],
                                   min_val=1500, max_val=9000, unit="K"))
            lamp.add_switch(Switch("color", SwitchType.COLOR, value=list(color[:3])))

            lamp.raw_info["_light_obj"] = light
            lamp.connected = True
            return True
        except Exception as e:
            logger.error("LIFX connect failed: %s", e)
            return False

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        light = lamp.raw_info.get("_light_obj")
        if not light:
            return False

        try:
            if switch_name == "power":
                light.set_power(65535 if value else 0)
            elif switch_name == "brightness":
                color = light.get_color()
                light.set_color([color[0], color[1], int(value), color[3]])
            elif switch_name == "color_temp":
                color = light.get_color()
                light.set_color([color[0], color[1], color[2], int(value)])
            elif switch_name == "color":
                if isinstance(value, (list, tuple)) and len(value) >= 3:
                    color = light.get_color()
                    light.set_color([value[0], value[1], value[2], color[3]])
            elif switch_name in ("hue", "saturation"):
                color = list(light.get_color())
                idx = 0 if switch_name == "hue" else 1
                color[idx] = int(value)
                light.set_color(color)
            else:
                return False

            if switch_name in lamp.switches:
                lamp.switches[switch_name].value = value
            return True
        except Exception as e:
            logger.error("LIFX set_switch failed: %s", e)
            return False

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        light = lamp.raw_info.get("_light_obj")
        if not light:
            return {}
        try:
            color = light.get_color()
            return {"power": light.get_power() > 0, "color": list(color)}
        except Exception:
            return {}
