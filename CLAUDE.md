# marksclock

Exhaustive time utility suite — clock, timers, stopwatch, world clock, converters, and more. Python + FastAPI backend with vanilla JS web UI.

## Quick Start

```bash
pip install -e .
marksclock serve              # start on 0.0.0.0:8080
marksclock serve --port 9090  # custom port
marksclock info               # show config
```

Then open `http://localhost:8080` (or LAN IP from phone).

## Architecture

- `marksclock/app.py` — FastAPI factory, router mounting, WebSocket, static files
- `marksclock/__main__.py` — CLI (click): serve, info
- `marksclock/config.py` — Settings from env vars
- `marksclock/state.py` — In-memory state + JSON persistence (~/.config/marksclock/)
- `marksclock/routers/` — One router per feature (11 total)
- `marksclock/services/` — Business logic (timezone, sun, date calc, etc.)
- `marksclock/static/` — CSS + JS (vanilla, ES modules, no build step)
- `marksclock/templates/index.html` — Single HTML shell (Jinja2)

## Features (21 modules)

Clock, Timer, Stopwatch, Alarms, Pomodoro, World Clock, Calendar, Timezone Converter, Time Difference, Duration Calculator, Age Calculator, Days Between, Day of Week, Week Number, Leap Year, Unix Timestamp, ISO 8601, Sunrise/Sunset, DST Reference, Timezone Reference, Meeting Planner.

## Environment Variables

| Var | Default | Description |
|-----|---------|-------------|
| `MARKSCLOCK_HOST` | `0.0.0.0` | Bind host |
| `MARKSCLOCK_PORT` | `8080` | Bind port |
| `MARKSCLOCK_TZ` | `America/New_York` | Default timezone |
| `MARKSCLOCK_LAT` | — | Home latitude (for sunrise/sunset) |
| `MARKSCLOCK_LON` | — | Home longitude |
| `MARKSCLOCK_STATE_DIR` | `~/.config/marksclock` | State persistence directory |

## Gotchas

- Sunrise/sunset requires lat/lon coordinates (set in `.env` or use browser geolocation)
- Alarm sounds require user to click "Enable Audio" (browser autoplay policy)
- State persists to `~/.config/marksclock/state.json` — delete to reset
- Timezone data comes from system tzdata (via Python `zoneinfo`)
