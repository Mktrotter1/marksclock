"""Meeting planner API — find overlapping business hours."""

from __future__ import annotations

from datetime import datetime, timezone, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class MeetingRequest(BaseModel):
    timezones: list[str]
    work_start: str = "09:00"  # HH:MM
    work_end: str = "17:00"    # HH:MM


@router.post("/overlap")
async def find_overlap(body: MeetingRequest) -> dict:
    ws_h, ws_m = map(int, body.work_start.split(":"))
    we_h, we_m = map(int, body.work_end.split(":"))

    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()

    # For each timezone, compute work hours in UTC
    utc_ranges = []
    for tz_name in body.timezones:
        zone = ZoneInfo(tz_name)
        local_start = datetime.combine(today, time(ws_h, ws_m), tzinfo=zone)
        local_end = datetime.combine(today, time(we_h, we_m), tzinfo=zone)
        utc_start = local_start.astimezone(timezone.utc)
        utc_end = local_end.astimezone(timezone.utc)
        utc_ranges.append({
            "timezone": tz_name,
            "utc_start": utc_start,
            "utc_end": utc_end,
        })

    # Find overlap
    latest_start = max(r["utc_start"] for r in utc_ranges)
    earliest_end = min(r["utc_end"] for r in utc_ranges)

    if latest_start >= earliest_end:
        return {
            "overlap": False,
            "message": "No overlapping business hours found",
            "zones": [{
                "timezone": r["timezone"],
                "work_start_utc": r["utc_start"].strftime("%H:%M"),
                "work_end_utc": r["utc_end"].strftime("%H:%M"),
            } for r in utc_ranges],
        }

    overlap_hours = (earliest_end - latest_start).total_seconds() / 3600

    # Convert overlap back to each timezone
    per_zone = []
    for r in utc_ranges:
        zone = ZoneInfo(r["timezone"])
        local_start = latest_start.astimezone(zone)
        local_end = earliest_end.astimezone(zone)
        per_zone.append({
            "timezone": r["timezone"],
            "overlap_start": local_start.strftime("%H:%M"),
            "overlap_end": local_end.strftime("%H:%M"),
        })

    return {
        "overlap": True,
        "overlap_hours": round(overlap_hours, 1),
        "overlap_utc_start": latest_start.strftime("%H:%M UTC"),
        "overlap_utc_end": earliest_end.strftime("%H:%M UTC"),
        "per_zone": per_zone,
    }
