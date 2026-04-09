"""World clock API — manage watched timezones."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from pydantic import BaseModel

from marksclock.state import app_state

router = APIRouter()


class AddZone(BaseModel):
    timezone: str


@router.get("")
async def list_zones() -> list[dict]:
    now_utc = datetime.now(timezone.utc)
    result = []
    for tz_name in app_state.worldclock_zones:
        try:
            zone = ZoneInfo(tz_name)
            local = now_utc.astimezone(zone)
            result.append({
                "timezone": tz_name,
                "time_24h": local.strftime("%H:%M:%S"),
                "time_12h": local.strftime("%I:%M:%S %p"),
                "date": local.strftime("%Y-%m-%d"),
                "day_of_week": local.strftime("%A"),
                "utc_offset": local.strftime("%z"),
                "abbreviation": local.tzname(),
            })
        except KeyError:
            continue
    return result


@router.post("")
async def add_zone(body: AddZone) -> dict:
    if body.timezone not in app_state.worldclock_zones:
        app_state.worldclock_zones.append(body.timezone)
        app_state.save()
    return {"zones": app_state.worldclock_zones}


@router.delete("/{tz_name:path}")
async def remove_zone(tz_name: str) -> dict:
    if tz_name in app_state.worldclock_zones:
        app_state.worldclock_zones.remove(tz_name)
        app_state.save()
    return {"zones": app_state.worldclock_zones}
