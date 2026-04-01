"""Magic Home / Flux LED protocol adapter - UDP discovery, TCP control."""

from __future__ import annotations

import logging
from typing import Any

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)


class MagicHomeProtocol(LampProtocol):
    name = "magic_home"

    async def discover(self, timeout: float = 5.0) -> list[Lamp]:
        try:
            from flux_led import BulbScanner
        except ImportError:
            logger.debug("flux_led not installed, skipping Magic Home discovery")
            return []

        lamps: list[Lamp] = []
        scanner = BulbScanner()
        scanner.scan(timeout=int(timeout))

        for dev in scanner.found_bulbs:
            lamp = Lamp(
                id=f"magic_home:{dev.get('id', dev.get('ipaddr', ''))}",
                name=dev.get("id", ""),
                ip=dev.get("ipaddr", ""),
                port=5577,
                protocol=self.name,
                model=dev.get("model", ""),
                raw_info=dev,
            )
            lamps.append(lamp)

        return lamps

    async def connect(self, lamp: Lamp) -> bool:
        try:
            from flux_led import WifiLedBulb
        except ImportError:
            return False

        try:
            bulb = WifiLedBulb(lamp.ip)
            bulb.update_state()

            lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=bulb.is_on))
            lamp.add_switch(Switch("brightness", SwitchType.RANGE,
                                   value=bulb.brightness, min_val=0, max_val=255))

            if bulb.rgbwcapable or True:  # most Magic Home support RGB
                r, g, b = bulb.getRgb()
                lamp.add_switch(Switch("color", SwitchType.COLOR, value=[r, g, b]))

            if hasattr(bulb, 'raw_state') and bulb.raw_state:
                lamp.add_switch(Switch("mode", SwitchType.SELECT,
                                       value=bulb.raw_state.mode if hasattr(bulb.raw_state, 'mode') else 0,
                                       options=[str(i) for i in range(0, 300)]))

            lamp.raw_info["_bulb_obj"] = bulb
            lamp.connected = True
            return True
        except Exception as e:
            logger.error("Magic Home connect failed: %s", e)
            return False

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        bulb = lamp.raw_info.get("_bulb_obj")
        if not bulb:
            return False

        try:
            if switch_name == "power":
                bulb.turnOn() if value else bulb.turnOff()
            elif switch_name == "brightness":
                r, g, b = bulb.getRgb()
                bulb.setRgb(r, g, b, brightness=int(value))
            elif switch_name == "color":
                if isinstance(value, (list, tuple)) and len(value) == 3:
                    bulb.setRgb(value[0], value[1], value[2])
            elif switch_name == "mode":
                bulb.setPresetPattern(int(value), 50)
            else:
                return False

            if switch_name in lamp.switches:
                lamp.switches[switch_name].value = value
            return True
        except Exception as e:
            logger.error("Magic Home set_switch failed: %s", e)
            return False

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        bulb = lamp.raw_info.get("_bulb_obj")
        if not bulb:
            return {}
        try:
            bulb.update_state()
            return {"power": bulb.is_on, "brightness": bulb.brightness, "rgb": bulb.getRgb()}
        except Exception:
            return {}
