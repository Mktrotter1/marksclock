"""Stopwatch API."""

from __future__ import annotations

import time

from fastapi import APIRouter

from marksclock.state import app_state, new_id, StopwatchState, StopwatchStatus

router = APIRouter()

DEFAULT_ID = "default"


def _get_or_create() -> StopwatchState:
    if DEFAULT_ID not in app_state.stopwatches:
        app_state.stopwatches[DEFAULT_ID] = StopwatchState(id=DEFAULT_ID)
    return app_state.stopwatches[DEFAULT_ID]


@router.get("")
async def get_stopwatch() -> dict:
    sw = _get_or_create()
    return {
        "id": sw.id, "status": sw.status,
        "elapsed": sw.current_elapsed(),
        "laps": sw.laps,
    }


@router.post("/start")
async def start() -> dict:
    sw = _get_or_create()
    if sw.status != StopwatchStatus.RUNNING:
        sw.started_at = time.time()
        sw.status = StopwatchStatus.RUNNING
        app_state.save()
    return {"status": sw.status, "elapsed": sw.current_elapsed()}


@router.post("/stop")
async def stop() -> dict:
    sw = _get_or_create()
    if sw.status == StopwatchStatus.RUNNING:
        sw.elapsed_seconds = sw.current_elapsed()
        sw.started_at = None
        sw.status = StopwatchStatus.STOPPED
        app_state.save()
    return {"status": sw.status, "elapsed": sw.elapsed_seconds}


@router.post("/lap")
async def lap() -> dict:
    sw = _get_or_create()
    sw.laps.append(sw.current_elapsed())
    app_state.save()
    return {"laps": sw.laps}


@router.post("/reset")
async def reset() -> dict:
    sw = _get_or_create()
    sw.elapsed_seconds = 0.0
    sw.started_at = None
    sw.status = StopwatchStatus.STOPPED
    sw.laps.clear()
    app_state.save()
    return {"status": sw.status, "elapsed": 0.0, "laps": []}
