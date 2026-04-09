"""Timezone reference API — full IANA database, DST transitions."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, available_timezones

from fastapi import APIRouter

router = APIRouter()


@router.get("/timezones")
async def list_timezones(filter: str | None = None) -> list[dict]:
    now_utc = datetime.now(timezone.utc)
    result = []
    for tz_name in sorted(available_timezones()):
        if filter and filter.lower() not in tz_name.lower():
            continue
        try:
            zone = ZoneInfo(tz_name)
            local = now_utc.astimezone(zone)
            result.append({
                "timezone": tz_name,
                "abbreviation": local.tzname(),
                "utc_offset": local.strftime("%z"),
                "utc_offset_hours": local.utcoffset().total_seconds() / 3600 if local.utcoffset() else 0,
            })
        except Exception:
            continue
    return result


@router.get("/dst/{tz_name:path}")
async def dst_transitions(tz_name: str, year: int | None = None) -> dict:
    target_year = year or datetime.now().year
    zone = ZoneInfo(tz_name)
    transitions = []

    # Walk through the year day by day to find offset changes
    prev_offset = None
    dt = datetime(target_year, 1, 1, tzinfo=timezone.utc).astimezone(zone)
    prev_offset = dt.utcoffset()

    for day in range(1, 366):
        dt = datetime(target_year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)
        local = dt.astimezone(zone)
        current_offset = local.utcoffset()
        if current_offset != prev_offset:
            transitions.append({
                "date": local.strftime("%Y-%m-%d"),
                "from_offset": str(prev_offset),
                "to_offset": str(current_offset),
                "from_abbr": "",
                "to_abbr": local.tzname(),
            })
        prev_offset = current_offset

    return {
        "timezone": tz_name,
        "year": target_year,
        "transitions": transitions,
        "observes_dst": len(transitions) > 0,
    }
