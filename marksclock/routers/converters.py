"""Converter APIs — timezone, unix, ISO 8601, duration, date math."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


# --- Timezone conversion ---

class TzConvert(BaseModel):
    time_iso: str
    from_tz: str
    to_tz: str


@router.post("/timezone")
async def convert_timezone(body: TzConvert) -> dict:
    dt = datetime.fromisoformat(body.time_iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(body.from_tz))
    result = dt.astimezone(ZoneInfo(body.to_tz))
    return {
        "from": {"timezone": body.from_tz, "time": dt.isoformat()},
        "to": {"timezone": body.to_tz, "time": result.isoformat()},
    }


# --- Unix timestamp ---

class UnixConvert(BaseModel):
    timestamp: float | None = None
    iso: str | None = None


@router.post("/unix")
async def convert_unix(body: UnixConvert) -> dict:
    if body.timestamp is not None:
        dt = datetime.fromtimestamp(body.timestamp, tz=timezone.utc)
        return {"timestamp": body.timestamp, "iso": dt.isoformat(), "human": dt.strftime("%Y-%m-%d %H:%M:%S UTC")}
    elif body.iso:
        dt = datetime.fromisoformat(body.iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return {"timestamp": dt.timestamp(), "iso": dt.isoformat(), "human": dt.strftime("%Y-%m-%d %H:%M:%S %Z")}
    return {"error": "provide timestamp or iso"}


# --- ISO 8601 ---

class IsoConvert(BaseModel):
    input: str


@router.post("/iso")
async def convert_iso(body: IsoConvert) -> dict:
    try:
        dt = datetime.fromisoformat(body.input)
        return {
            "iso": dt.isoformat(),
            "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H:%M:%S"),
            "timezone": str(dt.tzinfo) if dt.tzinfo else "naive",
            "epoch": dt.timestamp() if dt.tzinfo else None,
        }
    except ValueError:
        return {"error": f"Cannot parse: {body.input}"}


# --- Duration / time difference ---

class DurationCalc(BaseModel):
    start: str  # ISO
    end: str    # ISO


@router.post("/duration")
async def calc_duration(body: DurationCalc) -> dict:
    d1 = datetime.fromisoformat(body.start)
    d2 = datetime.fromisoformat(body.end)
    delta = d2 - d1
    total_seconds = delta.total_seconds()
    days = int(total_seconds // 86400)
    hours = int((total_seconds % 86400) // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return {
        "total_seconds": total_seconds,
        "days": days, "hours": hours, "minutes": minutes, "seconds": seconds,
        "human": f"{days}d {hours}h {minutes}m {seconds}s",
    }


# --- Date add/subtract ---

class DateAdd(BaseModel):
    date: str  # ISO date or datetime
    years: int = 0
    months: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0


@router.post("/date-add")
async def date_add(body: DateAdd) -> dict:
    dt = datetime.fromisoformat(body.date)
    result = dt + relativedelta(
        years=body.years, months=body.months, days=body.days,
        hours=body.hours, minutes=body.minutes, seconds=body.seconds,
    )
    return {"original": dt.isoformat(), "result": result.isoformat()}


# --- Date utilities ---

@router.get("/day-of-week")
async def day_of_week(date: str) -> dict:
    dt = datetime.fromisoformat(date)
    return {"date": date, "day_of_week": dt.strftime("%A"), "day_number": dt.weekday()}


@router.get("/week-number")
async def week_number(date: str) -> dict:
    dt = datetime.fromisoformat(date)
    iso_cal = dt.isocalendar()
    return {"date": date, "iso_week": iso_cal[1], "iso_year": iso_cal[0], "iso_day": iso_cal[2]}


@router.get("/leap-year")
async def leap_year(year: int) -> dict:
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    return {"year": year, "is_leap_year": is_leap}


@router.get("/age")
async def age(birthdate: str) -> dict:
    birth = datetime.fromisoformat(birthdate).date()
    today = datetime.now().date()
    rd = relativedelta(today, birth)
    total_days = (today - birth).days
    return {
        "birthdate": str(birth),
        "years": rd.years, "months": rd.months, "days": rd.days,
        "total_days": total_days,
        "human": f"{rd.years} years, {rd.months} months, {rd.days} days",
    }


@router.get("/days-between")
async def days_between(start: str, end: str) -> dict:
    d1 = datetime.fromisoformat(start).date()
    d2 = datetime.fromisoformat(end).date()
    delta = (d2 - d1).days
    return {"start": str(d1), "end": str(d2), "days": delta, "weeks": delta / 7}
