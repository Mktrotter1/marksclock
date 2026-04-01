"""Govee LAN protocol adapter - UDP multicast discovery and control."""

from __future__ import annotations

import json
import logging
import socket
import struct
from typing import Any

import asyncio

from markslamp.models import Lamp, Switch, SwitchType
from markslamp.protocols.base import LampProtocol

logger = logging.getLogger(__name__)

GOVEE_MULTICAST_GROUP = "239.255.255.250"
GOVEE_SCAN_PORT = 4001
GOVEE_CMD_PORT = 4003


class GoveeProtocol(LampProtocol):
    name = "govee"

    async def discover(self, timeout: float = 5.0) -> list[Lamp]:
        lamps: list[Lamp] = []

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", GOVEE_SCAN_PORT))

            mreq = struct.pack("4sl", socket.inet_aton(GOVEE_MULTICAST_GROUP), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            sock.settimeout(0.5)

            # Send scan request
            scan_msg = json.dumps({"msg": {"cmd": "scan", "data": {"account_topic": "reserve"}}})
            sock.sendto(scan_msg.encode(), (GOVEE_MULTICAST_GROUP, GOVEE_SCAN_PORT))

            end_time = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < end_time:
                try:
                    data, addr = sock.recvfrom(4096)
                    msg = json.loads(data.decode())
                    if msg.get("msg", {}).get("cmd") == "scan":
                        device = msg["msg"].get("data", {})
                        lamp = Lamp(
                            id=f"govee:{device.get('device', addr[0])}",
                            name=device.get("sku", "Govee Light"),
                            ip=addr[0],
                            port=GOVEE_CMD_PORT,
                            protocol=self.name,
                            model=device.get("sku", ""),
                            raw_info=device,
                        )
                        lamps.append(lamp)
                except socket.timeout:
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.debug("Govee recv error: %s", e)
                    break

            sock.close()
        except Exception as e:
            logger.debug("Govee discovery failed: %s", e)

        return lamps

    async def connect(self, lamp: Lamp) -> bool:
        # Govee LAN devices support power, brightness, and color via UDP
        lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=False))
        lamp.add_switch(Switch("brightness", SwitchType.RANGE, value=100,
                               min_val=0, max_val=100, unit="%"))
        lamp.add_switch(Switch("color", SwitchType.COLOR, value=[255, 255, 255]))
        lamp.add_switch(Switch("color_temp", SwitchType.RANGE, value=4000,
                               min_val=2000, max_val=9000, unit="K"))
        lamp.connected = True
        return True

    def _send_cmd(self, lamp: Lamp, cmd: dict) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(json.dumps(cmd).encode(), (lamp.ip, lamp.port))
            sock.close()
            return True
        except Exception as e:
            logger.error("Govee send failed: %s", e)
            return False

    async def set_switch(self, lamp: Lamp, switch_name: str, value: Any) -> bool:
        if switch_name == "power":
            cmd = {"msg": {"cmd": "turn", "data": {"value": 1 if value else 0}}}
        elif switch_name == "brightness":
            cmd = {"msg": {"cmd": "brightness", "data": {"value": int(value)}}}
        elif switch_name == "color":
            if isinstance(value, (list, tuple)) and len(value) == 3:
                cmd = {"msg": {"cmd": "colorwc", "data": {
                    "color": {"r": value[0], "g": value[1], "b": value[2]}, "colorTemInKelvin": 0
                }}}
            else:
                return False
        elif switch_name == "color_temp":
            cmd = {"msg": {"cmd": "colorwc", "data": {
                "color": {"r": 0, "g": 0, "b": 0}, "colorTemInKelvin": int(value)
            }}}
        else:
            return False

        ok = self._send_cmd(lamp, cmd)
        if ok and switch_name in lamp.switches:
            lamp.switches[switch_name].value = value
        return ok

    async def get_state(self, lamp: Lamp) -> dict[str, Any]:
        return {n: s.value for n, s in lamp.switches.items()}
