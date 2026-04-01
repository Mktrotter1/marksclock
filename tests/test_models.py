"""Tests for data models."""

from markslamp.models import Lamp, Switch, SwitchType


def test_switch_toggle_display():
    sw = Switch("power", SwitchType.TOGGLE, value=True)
    assert sw.display == "ON"
    sw.value = False
    assert sw.display == "OFF"


def test_switch_range_display():
    sw = Switch("brightness", SwitchType.RANGE, value=128, min_val=0, max_val=255)
    assert sw.display == "128"
    sw.unit = "%"
    assert sw.display == "128%"


def test_switch_color_display():
    sw = Switch("color", SwitchType.COLOR, value=[255, 0, 128])
    assert sw.display == "([255, 0, 128])"


def test_switch_select_display():
    sw = Switch("effect", SwitchType.SELECT, value="Rainbow", options=["Rainbow", "Fire", "Ocean"])
    assert sw.display == "Rainbow"


def test_lamp_creation():
    lamp = Lamp(id="test:1", name="Test Lamp", ip="192.168.1.100", port=80, protocol="wled")
    assert lamp.display_name == "Test Lamp"
    assert lamp.connected is False
    assert lamp.switches == {}


def test_lamp_display_name_fallback():
    lamp = Lamp(id="test:2", name="", ip="10.0.0.5", port=80, protocol="tuya")
    assert lamp.display_name == "tuya@10.0.0.5"


def test_lamp_add_switch():
    lamp = Lamp(id="test:3", name="My Lamp", ip="10.0.0.1", port=80, protocol="wled")
    sw = Switch("power", SwitchType.TOGGLE, value=True)
    lamp.add_switch(sw)

    assert "power" in lamp.switches
    assert lamp.switches["power"].value is True


def test_lamp_multiple_switches():
    lamp = Lamp(id="test:4", name="RGB Lamp", ip="10.0.0.1", port=80, protocol="lifx")
    lamp.add_switch(Switch("power", SwitchType.TOGGLE, value=True))
    lamp.add_switch(Switch("brightness", SwitchType.RANGE, value=200, min_val=0, max_val=255))
    lamp.add_switch(Switch("color", SwitchType.COLOR, value=[255, 128, 0]))
    lamp.add_switch(Switch("effect", SwitchType.SELECT, value="none", options=["none", "pulse"]))

    assert len(lamp.switches) == 4
    assert lamp.switches["brightness"].max_val == 255
    assert lamp.switches["color"].value == [255, 128, 0]
    assert lamp.switches["effect"].options == ["none", "pulse"]
