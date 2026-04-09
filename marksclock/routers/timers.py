"""Timer API — countdown timers."""

from __future__ import annotations

import time

from fastapi import APIRouter
from pydantic import BaseModel

from marksclock.state import app_state, new_id, TimerState, TimerStatus

router = APIRouter()


class CreateTimer(BaseModel):
    label: str = "Timer"
    duration_seconds: float


@router.get("")
async def list_timers() -> list[dict]:
    result = []
    for t in app_state.timers.values():
        t.tick()
        result.append({
            "id": t.id, "label": t.label, "duration": t.duration_seconds,
            "remaining": t.remaining_seconds, "status": t.status,
        })
    return result


@router.post("")
async def create_timer(body: CreateTimer) -> dict:
    tid = new_id()
    t = TimerState(
        id=tid, label=body.label,
        duration_seconds=body.duration_seconds,
        remaining_seconds=body.duration_seconds,
    )
    app_state.timers[tid] = t
    app_state.save()
    return {"id": tid, "status": t.status}


@router.post("/{timer_id}/start")
async def start_timer(timer_id: str) -> dict:
    t = app_state.timers.get(timer_id)
    if not t:
        return {"error": "not found"}
    t.status = TimerStatus.RUNNING
    t.started_at = time.time() - (t.duration_seconds - t.remaining_seconds)
    app_state.save()
    return {"id": t.id, "status": t.status}


@router.post("/{timer_id}/pause")
async def pause_timer(timer_id: str) -> dict:
    t = app_state.timers.get(timer_id)
    if not t:
        return {"error": "not found"}
    t.tick()
    t.status = TimerStatus.PAUSED
    t.started_at = None
    app_state.save()
    return {"id": t.id, "status": t.status, "remaining": t.remaining_seconds}


@router.post("/{timer_id}/reset")
async def reset_timer(timer_id: str) -> dict:
    t = app_state.timers.get(timer_id)
    if not t:
        return {"error": "not found"}
    t.remaining_seconds = t.duration_seconds
    t.status = TimerStatus.PAUSED
    t.started_at = None
    app_state.save()
    return {"id": t.id, "status": t.status}


@router.delete("/{timer_id}")
async def delete_timer(timer_id: str) -> dict:
    if timer_id in app_state.timers:
        del app_state.timers[timer_id]
        app_state.save()
    return {"ok": True}
