"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from marksclock.config import settings
from marksclock.routers import clock, timers, stopwatch, alarms, worldclock, pomodoro, converters, sun, reference, meeting, calendar as cal_router

BASE = Path(__file__).parent


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active.remove(ws)

    async def broadcast(self, data: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)


manager = ConnectionManager()


async def clock_ticker() -> None:
    """Background task: broadcast current time every second."""
    while True:
        now = datetime.now(timezone.utc)
        await manager.broadcast({
            "type": "clock_tick",
            "utc_iso": now.isoformat(),
            "utc_epoch": now.timestamp(),
        })
        await asyncio.sleep(1)


def create_app() -> FastAPI:
    app = FastAPI(title="marksclock", version="0.1.0")

    # Static files
    app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

    # Routers
    app.include_router(clock.router, prefix="/api/clock", tags=["clock"])
    app.include_router(timers.router, prefix="/api/timers", tags=["timers"])
    app.include_router(stopwatch.router, prefix="/api/stopwatch", tags=["stopwatch"])
    app.include_router(alarms.router, prefix="/api/alarms", tags=["alarms"])
    app.include_router(worldclock.router, prefix="/api/worldclock", tags=["worldclock"])
    app.include_router(pomodoro.router, prefix="/api/pomodoro", tags=["pomodoro"])
    app.include_router(converters.router, prefix="/api/convert", tags=["converters"])
    app.include_router(sun.router, prefix="/api/sun", tags=["sun"])
    app.include_router(reference.router, prefix="/api/reference", tags=["reference"])
    app.include_router(meeting.router, prefix="/api/meeting", tags=["meeting"])
    app.include_router(cal_router.router, prefix="/api/calendar", tags=["calendar"])

    # Jinja2 for index.html
    templates = Environment(loader=FileSystemLoader(BASE / "templates"), autoescape=True)

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        tpl = templates.get_template("index.html")
        return tpl.render(default_tz=settings.default_timezone)

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket) -> None:
        await manager.connect(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(ws)

    @app.on_event("startup")
    async def startup() -> None:
        asyncio.create_task(clock_ticker())

    return app
