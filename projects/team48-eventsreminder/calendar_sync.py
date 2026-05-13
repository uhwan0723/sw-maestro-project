"""구글캘린더 iCal 연동"""

from datetime import date, datetime, time

import requests
from icalendar import Calendar

def to_iso(value) -> str:
    decoded = value.dt if hasattr(value, "dt") else value
    if isinstance(decoded, datetime):
        if decoded.tzinfo:
            decoded = decoded.astimezone().replace(tzinfo=None)
        return decoded.isoformat()
    if isinstance(decoded, date):
        return datetime.combine(decoded, time.min).isoformat()
    return str(decoded)


def is_past(value) -> bool:
    decoded = value.dt if hasattr(value, "dt") else value
    if isinstance(decoded, datetime):
        now = datetime.now(decoded.tzinfo) if decoded.tzinfo else datetime.now()
        return decoded < now
    if isinstance(decoded, date):
        return decoded < date.today()
    return False


def fetch_events(ical_url: str) -> list[dict]:
    """iCal URL에서 일정 가져오기
    반환 형식:
    [
        {
            "id": "uid123",
            "title": "A기업 면접",
            "description": "1차 기술면접",
            "start_time": "2025-05-15T14:00:00",
            "end_time": "2025-05-15T15:00:00",
        },
        ...
    ]
    """
    response = requests.get(ical_url, timeout=10)
    response.raise_for_status()

    calendar = Calendar.from_ical(response.content)
    events = []

    for component in calendar.walk("VEVENT"):
        uid = component.get("uid")
        summary = component.get("summary")
        start = component.get("dtstart")
        end = component.get("dtend")

        if not uid or not summary or not start:
            continue

        if is_past(start):
            continue

        event = {
            "id": str(uid),
            "title": str(summary),
            "description": str(component.get("description", "")),
            "start_time": to_iso(start),
            "end_time": to_iso(end) if end else None,
        }
        events.append(event)

    return events
