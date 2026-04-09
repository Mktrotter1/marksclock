"""HTTP client for remote marksclock API access.

Allows phones, Raspberry Pis, and other devices to use a running
marksclock server as a shared timer/alarm/stopwatch service.

Usage from CLI:
    marksclock client timer create "Pizza" 600
    marksclock client timer list
    marksclock client stopwatch start
    marksclock client alarm create "Standup" 09:00

Usage as Python library:
    from marksclock.client import MarksclockClient
    c = MarksclockClient("http://192.168.1.100:8080")
    c.timer_create("Pizza", 600)
"""

from __future__ import annotations

import json
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError


class MarksclockClient:
    """Lightweight HTTP client — no dependencies beyond stdlib."""

    def __init__(self, base_url: str = "http://localhost:8080") -> None:
        self.base = base_url.rstrip("/")

    def _get(self, path: str) -> dict:
        req = Request(f"{self.base}/api{path}")
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def _post(self, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body or {}).encode() if body else b"{}"
        req = Request(f"{self.base}/api{path}", data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def _delete(self, path: str) -> dict:
        req = Request(f"{self.base}/api{path}", method="DELETE")
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def _patch(self, path: str) -> dict:
        req = Request(f"{self.base}/api{path}", method="PATCH")
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    # --- Clock ---
    def clock(self, tz: str | None = None) -> dict:
        q = f"?tz={tz}" if tz else ""
        return self._get(f"/clock{q}")

    # --- Timers ---
    def timer_list(self) -> list:
        return self._get("/timers")

    def timer_create(self, label: str, seconds: float) -> dict:
        return self._post("/timers", {"label": label, "duration_seconds": seconds})

    def timer_start(self, timer_id: str) -> dict:
        return self._post(f"/timers/{timer_id}/start")

    def timer_pause(self, timer_id: str) -> dict:
        return self._post(f"/timers/{timer_id}/pause")

    def timer_reset(self, timer_id: str) -> dict:
        return self._post(f"/timers/{timer_id}/reset")

    def timer_delete(self, timer_id: str) -> dict:
        return self._delete(f"/timers/{timer_id}")

    # --- Stopwatch ---
    def stopwatch(self) -> dict:
        return self._get("/stopwatch")

    def stopwatch_start(self) -> dict:
        return self._post("/stopwatch/start")

    def stopwatch_stop(self) -> dict:
        return self._post("/stopwatch/stop")

    def stopwatch_lap(self) -> dict:
        return self._post("/stopwatch/lap")

    def stopwatch_reset(self) -> dict:
        return self._post("/stopwatch/reset")

    # --- Alarms ---
    def alarm_list(self) -> list:
        return self._get("/alarms")

    def alarm_create(self, label: str, time_str: str, recurring: bool = False, days: list[int] | None = None) -> dict:
        return self._post("/alarms", {"label": label, "time_str": time_str, "recurring": recurring, "days": days or []})

    def alarm_toggle(self, alarm_id: str) -> dict:
        return self._patch(f"/alarms/{alarm_id}")

    def alarm_delete(self, alarm_id: str) -> dict:
        return self._delete(f"/alarms/{alarm_id}")

    # --- Pomodoro ---
    def pomodoro(self) -> dict:
        return self._get("/pomodoro")

    def pomodoro_start(self) -> dict:
        return self._post("/pomodoro/start")

    def pomodoro_pause(self) -> dict:
        return self._post("/pomodoro/pause")

    def pomodoro_skip(self) -> dict:
        return self._post("/pomodoro/skip")

    def pomodoro_reset(self) -> dict:
        return self._post("/pomodoro/reset")

    # --- World clock ---
    def worldclock(self) -> list:
        return self._get("/worldclock")

    def worldclock_add(self, tz: str) -> dict:
        return self._post("/worldclock", {"timezone": tz})

    def worldclock_remove(self, tz: str) -> dict:
        return self._delete(f"/worldclock/{tz}")

    # --- Converters ---
    def convert_timezone(self, time_iso: str, from_tz: str, to_tz: str) -> dict:
        return self._post("/convert/timezone", {"time_iso": time_iso, "from_tz": from_tz, "to_tz": to_tz})

    def convert_unix(self, timestamp: float | None = None, iso: str | None = None) -> dict:
        body = {}
        if timestamp is not None:
            body["timestamp"] = timestamp
        if iso:
            body["iso"] = iso
        return self._post("/convert/unix", body)

    # --- Sun ---
    def sun(self, lat: float, lon: float, date_str: str | None = None) -> dict:
        q = f"?lat={lat}&lon={lon}"
        if date_str:
            q += f"&date_str={date_str}"
        return self._get(f"/sun{q}")
