"""Protocol adapters for smart lamp control."""

from markslamp.protocols.base import LampProtocol
from markslamp.protocols.wled import WLEDProtocol
from markslamp.protocols.tuya import TuyaProtocol
from markslamp.protocols.lifx import LIFXProtocol
from markslamp.protocols.yeelight import YeelightProtocol
from markslamp.protocols.magic_home import MagicHomeProtocol
from markslamp.protocols.tasmota import TasmotaProtocol
from markslamp.protocols.esphome import ESPHomeProtocol
from markslamp.protocols.hue import HueProtocol
from markslamp.protocols.shelly import ShellyProtocol
from markslamp.protocols.govee import GoveeProtocol
from markslamp.protocols.elgato import ElgatoProtocol

ALL_PROTOCOLS: list[type[LampProtocol]] = [
    WLEDProtocol,
    TuyaProtocol,
    LIFXProtocol,
    YeelightProtocol,
    MagicHomeProtocol,
    TasmotaProtocol,
    ESPHomeProtocol,
    HueProtocol,
    ShellyProtocol,
    GoveeProtocol,
    ElgatoProtocol,
]

__all__ = [
    "LampProtocol",
    "ALL_PROTOCOLS",
    "WLEDProtocol",
    "TuyaProtocol",
    "LIFXProtocol",
    "YeelightProtocol",
    "MagicHomeProtocol",
    "TasmotaProtocol",
    "ESPHomeProtocol",
    "HueProtocol",
    "ShellyProtocol",
    "GoveeProtocol",
    "ElgatoProtocol",
]
