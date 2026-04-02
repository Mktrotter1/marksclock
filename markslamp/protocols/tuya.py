"""Tuya protocol adapter - UDP broadcast discovery, encrypted TCP control."""

from __future__ import annotations

import logging
from typing import Any

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)


class TuyaProtocol(LampProtocol):
    name = "tuya"

    async def discover(self, timeout: float = 5.0) -> list[Lamp]:
        try:
            import tinytuya
        except ImportError:
            logger.debug("tinytuya not installed, skipping Tuya discovery")
            return []

        lamps: list[Lamp] = []
        devices = tinytuya.deviceScan(maxretry=1, verbose=False)

        for dev_id, info in devices.items():
            if not isinstance(info, dict):
                continue
            lamp = Lamp(
                id=f"tuya:{dev_id}",
                name=info.get("name", dev_id),
                ip=info.get("ip", ""),
                port=int(info.get("port", 6668)),
                protocol=self.name,
                model=info.get("productKey", ""),
                firmware=info.get("version", ""),
                raw_info=info,
            )
            lamps.append(lamp)

        return lamps

    async def connect(self, lamp: Lamp) -> bool:
        try:
            import tinytuya
        except ImportError:
            return False

        dev_id = lamp.id.removeprefix("tuya:")
        local_key = lamp.raw_info.get("key", "")

        if not local_key:
            logger.warning("Tuya device %s has no local key - cloud setup required", dev_id)
            lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=None))
            lamp.add_switch(Switch("brightness", SwitchType.RANGE, value=None, min_val=10, max_val=1000))
            lamp.add_switch(Switch("color_temp", SwitchType.RANGE, value=None, min_val=0, max_val=1000))
            lamp.add_switch(Switch("color", SwitchType.COLOR, value=None))
            lamp.add_switch(Switch("mode", SwitchType.SELECT, value=None,
                                   options=["white", "colour", "scene", "music"]))
            lamp.connected = True
            return True

        try:
            d = tinytuya.BulbDevice(dev_id, lamp.ip, local_key)
            d.set_version(float(lamp.firmware or "3.3"))
            status = d.status()

            if "Error" in status:
                logger.error("Tuya status error: %s", status)
                return False

            dps = status.get("dps", {})

            lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=dps.get("20", dps.get("1", False))))
            lamp.add_switch(Switch("mode", SwitchType.SELECT, value=dps.get("21", "white"),
                                   options=["white", "colour", "scene", "music"]))
            lamp.add_switch(Switch("brightness", SwitchType.RANGE, value=dps.get("22", 0),
                                   min_val=10, max_val=1000))
            lamp.add_switch(Switch("color_temp", SwitchType.RANGE, value=dps.get("23", 0),
                                   min_val=0, max_val=1000))
            lamp.add_switch(Switch("color", SwitchType.COLOR, value=dps.get("24", "")))
            lamp.connected = True
            return True
        except Exception as e:
            logger.error("Tuya connect failed: %s", e)
            return False

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        try:
            import tinytuya
        except ImportError:
            return False

        dev_id = lamp.id.removeprefix("tuya:")
        local_key = lamp.raw_info.get("key", "")
        if not local_key:
            return False

        try:
            d = tinytuya.BulbDevice(dev_id, lamp.ip, local_key)
            d.set_version(float(lamp.firmware or "3.3"))

            if switch_name == "power":
                if value:
                    d.turn_on()
                else:
                    d.turn_off()
            elif switch_name == "brightness":
                d.set_brightness(int(value))
            elif switch_name == "color_temp":
                d.set_colourtemp(int(value))
            elif switch_name == "color":
                if isinstance(value, (list, tuple)) and len(value) == 3:
                    d.set_colour(value[0], value[1], value[2])
            elif switch_name == "mode":
                d.set_mode(str(value))
            else:
                return False

            if switch_name in lamp.switches:
                lamp.switches[switch_name].value = value
            return True
        except Exception as e:
            logger.error("Tuya set_switch failed: %s", e)
            return False

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        try:
            import tinytuya
        except ImportError:
            return {}

        dev_id = lamp.id.removeprefix("tuya:")
        local_key = lamp.raw_info.get("key", "")
        if not local_key:
            return {}

        try:
            d = tinytuya.BulbDevice(dev_id, lamp.ip, local_key)
            d.set_version(float(lamp.firmware or "3.3"))
            return d.status()
        except Exception:
            return {}
