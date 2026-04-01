# markslamp

Smart lamp scanner, discoverer, and controller. Finds lamps on the local network across 11 protocols and spawns switches for their controllable variables.

## Quick Start

```bash
pip install -e .
markslamp scan              # discover lamps
markslamp control           # interactive control
markslamp list-protocols    # show supported protocols
markslamp snapshot          # save state to JSON
```

## Architecture

- `markslamp/models.py` - Lamp, Switch, SwitchType data models
- `markslamp/scanner.py` - Concurrent multi-protocol discovery engine
- `markslamp/switch_manager.py` - Switch lifecycle, state tracking, event history
- `markslamp/protocols/` - One adapter per protocol (11 total)
- `markslamp/__main__.py` - CLI (click + rich)

## Protocols

WLED, Tuya, LIFX, Yeelight, Magic Home, Tasmota, ESPHome, Philips Hue, Shelly, Govee, Elgato Key Light.

Discovery uses mDNS (zeroconf), SSDP, and UDP broadcasts depending on protocol.

## Gotchas

- **Tuya** requires a one-time cloud lookup for local keys (set in `.env`)
- **Hue** requires pressing the bridge link button on first use
- **ESPHome** default password is empty string
- Firewall must allow mDNS (5353/udp), SSDP (1900/udp), and protocol-specific ports
