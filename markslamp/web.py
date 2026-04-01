"""Web UI server for markslamp - mobile-friendly lamp control."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from markslamp.models import Lamp, Switch
from markslamp.protocols import ALL_PROTOCOLS
from markslamp.scanner import Scanner
from markslamp.switch_manager import SwitchManager

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="markslamp", version="0.1.0")

# Global state
_mgr: SwitchManager | None = None
_scan_timeout: float = 5.0
_protocol_filter: list[str] | None = None


def get_manager() -> SwitchManager:
    global _mgr
    if _mgr is None:
        protos = [p() for p in ALL_PROTOCOLS]
        _mgr = SwitchManager(protos)
    return _mgr


def _serialize_switch(sw: Switch) -> dict[str, Any]:
    return {
        "type": sw.switch_type.value,
        "value": sw.value,
        "min_val": sw.min_val,
        "max_val": sw.max_val,
        "options": sw.options,
        "unit": sw.unit,
    }


def _serialize_lamps(mgr: SwitchManager) -> dict[str, Any]:
    result = {}
    for lamp_id, lamp in mgr.lamps.items():
        result[lamp_id] = {
            "name": lamp.display_name,
            "ip": lamp.ip,
            "port": lamp.port,
            "protocol": lamp.protocol,
            "model": lamp.model,
            "firmware": lamp.firmware,
            "connected": lamp.connected,
            "switches": {name: _serialize_switch(sw) for name, sw in lamp.switches.items()},
        }
    return result


@app.get("/", response_class=HTMLResponse)
async def index():
    return (TEMPLATES_DIR / "index.html").read_text()


@app.post("/api/scan")
async def api_scan():
    global _mgr

    all_protos = [p() for p in ALL_PROTOCOLS]
    if _protocol_filter:
        names = {p.lower() for p in _protocol_filter}
        all_protos = [p for p in all_protos if p.name in names]

    scanner = Scanner(all_protos, timeout=_scan_timeout)
    await scanner.scan()
    connected = await scanner.connect_all()

    _mgr = SwitchManager(all_protos)
    _mgr.register_all(connected)

    return {"ok": True, "count": len(_mgr.lamps), "lamps": _serialize_lamps(_mgr)}


@app.get("/api/lamps")
async def api_lamps():
    mgr = get_manager()
    return {"lamps": _serialize_lamps(mgr)}


class SwitchRequest(BaseModel):
    lamp_id: str
    switch_name: str
    value: Any


@app.post("/api/switch")
async def api_set_switch(req: SwitchRequest):
    mgr = get_manager()
    ok = await mgr.set_switch(req.lamp_id, req.switch_name, req.value)
    return {"ok": ok}


@app.post("/api/toggle/{lamp_id}")
async def api_toggle(lamp_id: str):
    mgr = get_manager()
    ok = await mgr.toggle_power(lamp_id)
    return {"ok": ok}


@app.get("/api/refresh/{lamp_id}")
async def api_refresh(lamp_id: str):
    mgr = get_manager()
    state = await mgr.refresh_state(lamp_id)
    return {"state": state}


def create_app(
    timeout: float = 5.0,
    protocols: list[str] | None = None,
) -> FastAPI:
    """Create configured app instance."""
    global _scan_timeout, _protocol_filter
    _scan_timeout = timeout
    _protocol_filter = protocols
    return app
