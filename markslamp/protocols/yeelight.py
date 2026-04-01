"""Yeelight protocol adapter - SSDP discovery, TCP JSON control."""

from __future__ import annotations

import logging
from typing import Any

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)


class YeelightProtocol(LampProtocol):
    name = "yeelight"

    async def discover(self, timeout: float = 5.0) -> list[Lamp]:
        try:
            from yeelight import discover_bulbs
        except ImportError:
            logger.debug("yeelight not installed, skipping Yeelight discovery")
            return []

        lamps: list[Lamp] = []
        bulbs = discover_bulbs(timeout=int(timeout))

        for b in bulbs:
            cap = b.get("capabilities", {})
            lamp = Lamp(
                id=f"yeelight:{cap.get('id', b.get('ip', ''))}",
                name=cap.get("name", ""),
                ip=b.get("ip", ""),
                port=int(b.get("port", 55443)),
                protocol=self.name,
                model=cap.get("model", ""),
                firmware=cap.get("fw_ver", ""),
                raw_info=b,
            )
            lamps.append(lamp)

        return lamps

    async def connect(self, lamp: Lamp) -> bool:
        try:
            from yeelight import Bulb
        except ImportError:
            return False

        try:
            bulb = Bulb(lamp.ip, port=lamp.port)
            props = bulb.get_properties()

            lamp.add_switch(Switch("power", SwitchType.TOGGLE,
                                   value=props.get("power") == "on"))
            lamp.add_switch(Switch("brightness", SwitchType.RANGE,
                                   value=int(props.get("bright", 0)),
                                   min_val=1, max_val=100, unit="%"))
            lamp.add_switch(Switch("color_temp", SwitchType.RANGE,
                                   value=int(props.get("ct", 4000)),
                                   min_val=1700, max_val=6500, unit="K"))

            rgb = int(props.get("rgb", 0))
            r, g, b_val = (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF
            lamp.add_switch(Switch("color", SwitchType.COLOR, value=[r, g, b_val]))

            lamp.add_switch(Switch("color_mode", SwitchType.SELECT,
                                   value=props.get("color_mode", "1"),
                                   options=["1", "2", "3"]))  # 1=RGB, 2=CT, 3=HSV

            lamp.raw_info["_bulb_obj"] = bulb
            lamp.connected = True
            return True
        except Exception as e:
            logger.error("Yeelight connect failed: %s", e)
            return False

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        bulb = lamp.raw_info.get("_bulb_obj")
        if not bulb:
            return False

        try:
            if switch_name == "power":
                bulb.turn_on() if value else bulb.turn_off()
            elif switch_name == "brightness":
                bulb.set_brightness(int(value))
            elif switch_name == "color_temp":
                bulb.set_color_temp(int(value))
            elif switch_name == "color":
                if isinstance(value, (list, tuple)) and len(value) == 3:
                    bulb.set_rgb(value[0], value[1], value[2])
            else:
                return False

            if switch_name in lamp.switches:
                lamp.switches[switch_name].value = value
            return True
        except Exception as e:
            logger.error("Yeelight set_switch failed: %s", e)
            return False

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        bulb = lamp.raw_info.get("_bulb_obj")
        if not bulb:
            return {}
        try:
            return bulb.get_properties()
        except Exception:
            return {}
