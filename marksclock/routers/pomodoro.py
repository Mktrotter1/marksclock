"""Pomodoro timer API."""

from __future__ import annotations

import time

from fastapi import APIRouter
from pydantic import BaseModel

from marksclock.state import app_state, PomodoroPhase

router = APIRouter()


class PomodoroConfig(BaseModel):
    work_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    sessions_before_long: int = 4


def _remaining() -> float:
    p = app_state.pomodoro
    if p.phase == PomodoroPhase.IDLE or not p.started_at:
        return p.remaining_seconds
    elapsed = time.time() - p.started_at
    return max(0, p.remaining_seconds - elapsed)


@router.get("")
async def get_state() -> dict:
    p = app_state.pomodoro
    return {
        "phase": p.phase,
        "remaining": _remaining(),
        "completed_sessions": p.completed_sessions,
        "work_minutes": p.work_minutes,
        "short_break_minutes": p.short_break_minutes,
        "long_break_minutes": p.long_break_minutes,
    }


@router.post("/start")
async def start() -> dict:
    p = app_state.pomodoro
    if p.phase == PomodoroPhase.IDLE:
        p.phase = PomodoroPhase.WORK
        p.remaining_seconds = p.work_minutes * 60
    p.started_at = time.time()
    app_state.save()
    return await get_state()


@router.post("/pause")
async def pause() -> dict:
    p = app_state.pomodoro
    if p.started_at:
        p.remaining_seconds = _remaining()
        p.started_at = None
        app_state.save()
    return await get_state()


@router.post("/skip")
async def skip() -> dict:
    p = app_state.pomodoro
    if p.phase == PomodoroPhase.WORK:
        p.completed_sessions += 1
        if p.completed_sessions % p.sessions_before_long == 0:
            p.phase = PomodoroPhase.LONG_BREAK
            p.remaining_seconds = p.long_break_minutes * 60
        else:
            p.phase = PomodoroPhase.SHORT_BREAK
            p.remaining_seconds = p.short_break_minutes * 60
    elif p.phase in (PomodoroPhase.SHORT_BREAK, PomodoroPhase.LONG_BREAK):
        p.phase = PomodoroPhase.WORK
        p.remaining_seconds = p.work_minutes * 60
    p.started_at = time.time()
    app_state.save()
    return await get_state()


@router.post("/reset")
async def reset() -> dict:
    p = app_state.pomodoro
    p.phase = PomodoroPhase.IDLE
    p.completed_sessions = 0
    p.started_at = None
    p.remaining_seconds = 0
    app_state.save()
    return await get_state()


@router.get("/config")
async def get_config() -> dict:
    p = app_state.pomodoro
    return {
        "work_minutes": p.work_minutes,
        "short_break_minutes": p.short_break_minutes,
        "long_break_minutes": p.long_break_minutes,
        "sessions_before_long": p.sessions_before_long,
    }


@router.put("/config")
async def set_config(body: PomodoroConfig) -> dict:
    p = app_state.pomodoro
    p.work_minutes = body.work_minutes
    p.short_break_minutes = body.short_break_minutes
    p.long_break_minutes = body.long_break_minutes
    p.sessions_before_long = body.sessions_before_long
    app_state.save()
    return await get_config()
