# marksclock

Self-hosted, exhaustive **time-utility suite** — clock, timers, stopwatch, alarms, Pomodoro, world clock, calendar, timezone/duration/age converters, sunrise–sunset, meeting planner, and more (21 modules). FastAPI backend + vanilla-JS web UI (no build step), reachable on the LAN from a phone or desktop.

> **Naming:** the project is **marksclock** — matches `pyproject.toml`, this folder, and the `marksclock.git` remote. The directory was renamed from `markslamp` → `marksclock` on 2026-06-16 to remove the legacy mismatch.

## Quick start

```bash
pip install -e .
marksclock serve              # http://0.0.0.0:8080
marksclock serve --port 9090  # custom port
marksclock info               # show resolved config
```

Then open `http://localhost:8080` (or `http://<lan-ip>:8080` from your phone).

## Stack
- Python 3.11+ — FastAPI, `uvicorn[standard]`, click CLI, astral (sun times)
- Vanilla JS (ES modules) + Jinja2 single-page shell
- State persisted as JSON under `~/.config/marksclock/`

## Config (env / `.env`)
`MARKSCLOCK_HOST` · `MARKSCLOCK_PORT` · `MARKSCLOCK_TZ` · `MARKSCLOCK_LAT` · `MARKSCLOCK_LON` · `MARKSCLOCK_STATE_DIR`
(Sunrise/sunset needs `MARKSCLOCK_LAT`/`LON`, or use browser geolocation.)

See **CLAUDE.md** for full architecture, the per-feature router map, and gotchas.
