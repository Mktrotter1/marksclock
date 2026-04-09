"""Calendar API — month/week grid data."""

from __future__ import annotations

import calendar
from datetime import date, datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/{year}/{month}")
async def month_data(year: int, month: int) -> dict:
    cal = calendar.Calendar(firstweekday=0)  # Monday start
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        week_data = []
        for day in week:
            week_data.append({
                "date": str(day),
                "day": day.day,
                "in_month": day.month == month,
                "is_today": day == date.today(),
                "day_of_week": day.strftime("%A"),
                "iso_week": day.isocalendar()[1],
            })
        weeks.append(week_data)

    return {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "weeks": weeks,
        "days_in_month": calendar.monthrange(year, month)[1],
    }
