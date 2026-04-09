"""Sunrise/sunset API using astral."""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta

from astral import LocationInfo
from astral.sun import sun
from fastapi import APIRouter

from marksclock.config import settings

router = APIRouter()


def _lon_to_tz(lon: float) -> timezone:
    """Approximate timezone from longitude for correct astral day boundaries."""
    offset_hours = round(lon / 15)
    return timezone(timedelta(hours=offset_hours))


@router.get("")
async def sun_times(
    lat: float | None = None,
    lon: float | None = None,
    city: str | None = None,
    date_str: str | None = None,
) -> dict:
    if city:
        if lat is None or lon is None:
            return {"error": "City lookup not supported yet — provide lat/lon"}

    latitude = lat or settings.home_lat
    longitude = lon or settings.home_lon

    if latitude is None or longitude is None:
        return {"error": "No coordinates provided. Set MARKSCLOCK_LAT/LON in .env or pass lat/lon params."}

    target_date = date.today()
    if date_str:
        target_date = date.fromisoformat(date_str)

    loc = LocationInfo("Home", "", "", latitude, longitude)
    local_tz = _lon_to_tz(longitude)
    s = sun(loc.observer, date=target_date, tzinfo=local_tz)
    day_length_seconds = (s["sunset"] - s["sunrise"]).total_seconds()

    return {
        "date": str(target_date),
        "latitude": latitude,
        "longitude": longitude,
        "dawn": s["dawn"].isoformat(),
        "sunrise": s["sunrise"].isoformat(),
        "noon": s["noon"].isoformat(),
        "sunset": s["sunset"].isoformat(),
        "dusk": s["dusk"].isoformat(),
        "day_length_hours": round(day_length_seconds / 3600, 2),
    }
