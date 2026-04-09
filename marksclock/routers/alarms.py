"""Alarms API — one-time and recurring alarms."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from marksclock.state import app_state, new_id, AlarmState

router = APIRouter()


class CreateAlarm(BaseModel):
    label: str = "Alarm"
    time_str: str  # HH:MM
    recurring: bool = False
    days: list[int] = []  # 0=Mon..6=Sun


@router.get("")
async def list_alarms() -> list[dict]:
    return [
        {"id": a.id, "label": a.label, "time": a.time_str,
         "enabled": a.enabled, "recurring": a.recurring, "days": a.days}
        for a in app_state.alarms.values()
    ]


@router.post("")
async def create_alarm(body: CreateAlarm) -> dict:
    aid = new_id()
    alarm = AlarmState(
        id=aid, label=body.label, time_str=body.time_str,
        recurring=body.recurring, days=body.days,
    )
    app_state.alarms[aid] = alarm
    app_state.save()
    return {"id": aid}


@router.patch("/{alarm_id}")
async def toggle_alarm(alarm_id: str) -> dict:
    a = app_state.alarms.get(alarm_id)
    if not a:
        return {"error": "not found"}
    a.enabled = not a.enabled
    app_state.save()
    return {"id": a.id, "enabled": a.enabled}


@router.delete("/{alarm_id}")
async def delete_alarm(alarm_id: str) -> dict:
    if alarm_id in app_state.alarms:
        del app_state.alarms[alarm_id]
        app_state.save()
    return {"ok": True}
