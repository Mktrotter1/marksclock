"""In-memory state with JSON file persistence."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

from marksclock.config import settings


class TimerStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"


class StopwatchStatus(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"


class PomodoroPhase(str, Enum):
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"
    IDLE = "idle"


@dataclass
class TimerState:
    id: str
    label: str
    duration_seconds: float
    remaining_seconds: float
    status: str = TimerStatus.PAUSED
    started_at: float | None = None

    def tick(self) -> None:
        if self.status == TimerStatus.RUNNING and self.started_at:
            elapsed = time.time() - self.started_at
            self.remaining_seconds = max(0, self.duration_seconds - elapsed)
            if self.remaining_seconds <= 0:
                self.status = TimerStatus.FINISHED


@dataclass
class StopwatchState:
    id: str
    status: str = StopwatchStatus.STOPPED
    elapsed_seconds: float = 0.0
    started_at: float | None = None
    laps: list[float] = field(default_factory=list)

    def current_elapsed(self) -> float:
        if self.status == StopwatchStatus.RUNNING and self.started_at:
            return self.elapsed_seconds + (time.time() - self.started_at)
        return self.elapsed_seconds


@dataclass
class AlarmState:
    id: str
    label: str
    time_str: str  # HH:MM
    enabled: bool = True
    recurring: bool = False
    days: list[int] = field(default_factory=list)  # 0=Mon..6=Sun


@dataclass
class PomodoroState:
    phase: str = PomodoroPhase.IDLE
    work_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    sessions_before_long: int = 4
    completed_sessions: int = 0
    started_at: float | None = None
    remaining_seconds: float = 0.0


@dataclass
class AppState:
    timers: dict[str, TimerState] = field(default_factory=dict)
    stopwatches: dict[str, StopwatchState] = field(default_factory=dict)
    alarms: dict[str, AlarmState] = field(default_factory=dict)
    pomodoro: PomodoroState = field(default_factory=PomodoroState)
    worldclock_zones: list[str] = field(default_factory=lambda: ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"])

    def save(self) -> None:
        path = settings.state_dir / "state.json"
        settings.state_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> AppState:
        path = settings.state_dir / "state.json"
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text())
            state = cls()
            for tid, t in data.get("timers", {}).items():
                state.timers[tid] = TimerState(**t)
            for sid, s in data.get("stopwatches", {}).items():
                state.stopwatches[sid] = StopwatchState(**s)
            for aid, a in data.get("alarms", {}).items():
                state.alarms[aid] = AlarmState(**a)
            pom = data.get("pomodoro", {})
            if pom:
                state.pomodoro = PomodoroState(**pom)
            state.worldclock_zones = data.get("worldclock_zones", state.worldclock_zones)
            return state
        except (json.JSONDecodeError, TypeError, KeyError):
            return cls()


def new_id() -> str:
    return uuid.uuid4().hex[:8]


# Singleton
app_state = AppState.load()
