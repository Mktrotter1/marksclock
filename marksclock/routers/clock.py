"""Clock API — current time in various formats."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter

from marksclock.config import settings

router = APIRouter()


@router.get("")
async def current_time(tz: str | None = None) -> dict:
    zone_name = tz or settings.default_timezone
    zone = ZoneInfo(zone_name)
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(zone)

    return {
        "timezone": zone_name,
        "iso": now_local.isoformat(),
        "time_24h": now_local.strftime("%H:%M:%S"),
        "time_12h": now_local.strftime("%I:%M:%S %p"),
        "date": now_local.strftime("%Y-%m-%d"),
        "day_of_week": now_local.strftime("%A"),
        "week_number": now_local.isocalendar()[1],
        "utc_offset": now_local.strftime("%z"),
        "epoch": now_utc.timestamp(),
    }
