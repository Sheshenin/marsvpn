"""iCal calendar fetching and parsing."""

from datetime import date, datetime, timedelta

import httpx
from icalendar import Calendar


def fetch_ical(url: str, timeout: float = 30.0) -> Calendar:
    """Download and parse an iCal feed."""
    resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    return Calendar.from_ical(resp.content)


def _to_date(dt_val) -> date:
    """Convert icalendar dt to date."""
    if isinstance(dt_val, datetime):
        return dt_val.date()
    if isinstance(dt_val, date):
        return dt_val
    return date.fromisoformat(str(dt_val))


def _event_to_dict(component) -> dict:
    """Extract useful fields from a VEVENT component."""
    dtstart = component.get("dtstart")
    dtend = component.get("dtend")
    start_dt = dtstart.dt if dtstart else None
    end_dt = dtend.dt if dtend else None

    is_all_day = isinstance(start_dt, date) and not isinstance(start_dt, datetime)

    return {
        "summary": str(component.get("summary", "")),
        "description": str(component.get("description", "")),
        "location": str(component.get("location", "")),
        "start": start_dt.isoformat() if start_dt else None,
        "end": end_dt.isoformat() if end_dt else None,
        "all_day": is_all_day,
    }


def get_events(url: str, days_back: int = 7, days_forward: int = 7) -> list[dict]:
    """Fetch iCal and return events within the date range."""
    cal = fetch_ical(url)
    today = date.today()
    range_start = today - timedelta(days=days_back)
    range_end = today + timedelta(days=days_forward)

    events = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        dtstart = component.get("dtstart")
        if not dtstart:
            continue
        event_date = _to_date(dtstart.dt)
        if range_start <= event_date <= range_end:
            events.append(_event_to_dict(component))

    events.sort(key=lambda e: e["start"] or "")
    return events


def get_today_tomorrow_events(url: str) -> list[dict]:
    """Fetch events for today and tomorrow only."""
    return get_events(url, days_back=0, days_forward=1)
