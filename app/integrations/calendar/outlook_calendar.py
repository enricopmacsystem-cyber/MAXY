from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.core.exceptions import CalendarError
from app.schemas.calendar import CalendarEvent

GRAPH_API = "https://graph.microsoft.com/v1.0"
_OUTLOOK_COLOR = "#0078D4"


def list_events(
    access_token: str,
    *,
    start: datetime,
    end: datetime,
) -> list[CalendarEvent]:
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "startDateTime": start.isoformat().replace("+00:00", "Z"),
        "endDateTime": end.isoformat().replace("+00:00", "Z"),
        "$top": 200,
        "$orderby": "start/dateTime",
        "$select": "id,subject,bodyPreview,start,end,location,isAllDay,organizer",
    }
    url = f"{GRAPH_API}/me/calendarView"
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=params)
    if response.status_code == 403:
        raise CalendarError(
            "Permesso calendario Outlook mancante. Scollegare e ricollegare l'account "
            "Outlook dalla scheda Posta per autorizzare Calendars.Read."
        )
    if response.status_code >= 400:
        raise CalendarError(f"Errore lettura calendario Outlook: {response.text[:300]}")

    events: list[CalendarEvent] = []
    for item in response.json().get("value", []):
        start_info = item.get("start") or {}
        end_info = item.get("end") or {}
        start_at = _parse_graph_datetime(start_info.get("dateTime"), start_info.get("timeZone"))
        end_at = _parse_graph_datetime(end_info.get("dateTime"), end_info.get("timeZone"))
        if not start_at:
            continue
        location = (item.get("location") or {}).get("displayName")
        organizer = (item.get("organizer") or {}).get("emailAddress") or {}
        events.append(
            CalendarEvent(
                id=f"outlook:{item.get('id', '')}",
                source="outlook",
                title=item.get("subject") or "(Senza titolo)",
                start_at=start_at,
                end_at=end_at,
                location=str(location) if location else None,
                description=str(item.get("bodyPreview") or "") or None,
                customer=organizer.get("name") or organizer.get("address"),
                all_day=bool(item.get("isAllDay")),
                color=_OUTLOOK_COLOR,
            )
        )
    return events


def _parse_graph_datetime(value: str | None, _tz: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None
