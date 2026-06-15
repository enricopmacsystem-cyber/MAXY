from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from app.core.logging import get_logger
from app.integrations.easyone.endpoints import EasyOneEndpoints
from app.integrations.easyone.http_client import EasyOneHttpClient
from app.integrations.easyone.orders_client import EasyOneOrdersClient
from app.integrations.easyone.response_utils import extract_easyone_items, macsystem_list_params
from app.schemas.calendar import CalendarEvent

logger = get_logger(__name__)

_EASYONE_COLOR = "#E67E22"
_PAGE_SIZE = 200
_MAX_PAGES = 50


class EasyOneCalendarClient:
    """Recupera appuntamenti/agenda da EasyOne CRM (endpoint configurabile + fallback ordini)."""

    def __init__(self, http_client: EasyOneHttpClient) -> None:
        self.http = http_client
        self.endpoints = EasyOneEndpoints.from_settings(http_client.settings)
        self.settings = http_client.settings

    def list_events(self, *, start: datetime, end: datetime) -> tuple[list[CalendarEvent], list[str]]:
        warnings: list[str] = []
        by_id: dict[str, CalendarEvent] = {}

        for path in self._calendar_paths():
            fetched = self._fetch_path_paginated(path, start=start, end=end)
            if not fetched:
                continue
            for event in fetched:
                by_id[event.id] = event

        events = list(by_id.values())

        if not events:
            warnings.append(
                "Agenda EasyOne: endpoint calendario non disponibile; "
                "mostrati ordini/joborders come attività pianificate."
            )
            events = self._orders_as_events(start=start, end=end)

        events = [event for event in events if start <= event.start_at <= end]
        events.sort(key=lambda item: item.start_at)
        return events, warnings

    def _fetch_path_paginated(
        self,
        path: str,
        *,
        start: datetime,
        end: datetime,
    ) -> list[CalendarEvent]:
        collected: list[CalendarEvent] = []
        seen_signatures: set[frozenset[str]] = set()
        skip = 0

        for _page in range(_MAX_PAGES):
            batch = self._fetch_page(path, start=start, end=end, take=_PAGE_SIZE, skip=skip)
            if not batch:
                break

            signature = frozenset(event.id for event in batch)
            if signature in seen_signatures:
                break
            seen_signatures.add(signature)
            collected.extend(batch)

            if len(batch) < _PAGE_SIZE:
                break
            skip += len(batch)

        return collected

    def _fetch_page(
        self,
        path: str,
        *,
        start: datetime,
        end: datetime,
        take: int,
        skip: int,
    ) -> list[CalendarEvent]:
        param_sets = (
            {
                "startDate": start.date().isoformat(),
                "endDate": end.date().isoformat(),
                "fromDate": start.date().isoformat(),
                "toDate": end.date().isoformat(),
                "take": take,
                "skip": skip,
            },
            macsystem_list_params(take=take, skip=skip),
            {
                **macsystem_list_params(take=take, skip=skip),
                "fromDate": start.date().isoformat(),
                "toDate": end.date().isoformat(),
            },
        )

        for params in param_sets:
            try:
                payload = self.http.get(path, params=params)
            except Exception as exc:
                logger.debug("EasyOne calendar %s %s: %s", path, params, exc)
                continue

            parsed = self._parse_payload(payload, start=start, end=end)
            if parsed:
                return parsed
        return []

    def _calendar_paths(self) -> list[str]:
        configured = (self.settings.easyone_path_calendar_events or "").strip()
        paths: list[str] = []
        if configured:
            paths.append(configured)
        paths.extend(
            [
                "/calendar/events",
                "/calendar/appointments",
                "/activities",
                "/appointments",
                "/Calendar/GetEvents",
                "/calendar",
            ]
        )
        seen: set[str] = set()
        unique: list[str] = []
        for path in paths:
            if path not in seen:
                seen.add(path)
                unique.append(path)
        return unique

    def _parse_payload(
        self,
        payload: dict[str, Any] | list[Any],
        *,
        start: datetime,
        end: datetime,
    ) -> list[CalendarEvent]:
        items: list[Any]
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = extract_easyone_items(payload)
            if not items:
                items = (
                    payload.get("events")
                    or payload.get("appointments")
                    or payload.get("activities")
                    or []
                )
        else:
            return []

        events: list[CalendarEvent] = []
        for index, raw in enumerate(items):
            if not isinstance(raw, dict):
                continue
            event = self._parse_item(raw, index=index)
            if event and start <= event.start_at <= end:
                events.append(event)
        return events

    def _parse_item(self, raw: dict[str, Any], *, index: int) -> CalendarEvent | None:
        title = (
            raw.get("title")
            or raw.get("subject")
            or raw.get("description")
            or raw.get("name")
            or raw.get("activityType")
            or raw.get("typeDescription")
            or "Attività EasyOne"
        )
        start_at = self._parse_datetime(
            raw.get("start")
            or raw.get("startDate")
            or raw.get("startDateTime")
            or raw.get("from")
            or raw.get("date")
            or raw.get("scheduledDate")
            or raw.get("activityDate")
        )
        if not start_at:
            return None
        end_at = self._parse_datetime(
            raw.get("end")
            or raw.get("endDate")
            or raw.get("endDateTime")
            or raw.get("to")
            or raw.get("dueDate")
        )
        if not end_at:
            end_at = start_at + timedelta(hours=1)
        event_id = str(
            raw.get("id")
            or raw.get("eventId")
            or raw.get("appointmentId")
            or raw.get("guid")
            or f"eo-{index}-{int(start_at.timestamp())}"
        )
        customer_raw = raw.get("customer")
        if isinstance(customer_raw, dict):
            customer = customer_raw.get("description") or customer_raw.get("code")
        else:
            customer = raw.get("customerName") or raw.get("customerCode") or customer_raw
        return CalendarEvent(
            id=f"easyone:{event_id}",
            source="easyone",
            title=str(title),
            start_at=start_at,
            end_at=end_at,
            location=str(raw.get("location") or raw.get("place") or "") or None,
            description=str(raw.get("notes") or raw.get("body") or raw.get("detail") or "") or None,
            customer=str(customer) if customer else None,
            all_day=bool(raw.get("allDay") or raw.get("isAllDay")),
            color=_EASYONE_COLOR,
        )

    def _orders_as_events(self, *, start: datetime, end: datetime) -> list[CalendarEvent]:
        orders_client = EasyOneOrdersClient(self.http)
        events: list[CalendarEvent] = []
        skip = 0

        for _page in range(_MAX_PAGES):
            headers = orders_client.search(from_date=start.date(), limit=_PAGE_SIZE, skip=skip)
            if not headers:
                break

            for header in headers:
                parsed = orders_client.parse_order(header)
                if not parsed:
                    continue
                order_date = parsed["order_date"]
                start_at = datetime.combine(order_date, time(hour=9), tzinfo=UTC)
                if start_at < start or start_at > end:
                    continue
                customer = parsed.get("customer_code") or ""
                events.append(
                    CalendarEvent(
                        id=f"easyone:order:{parsed['order_number']}",
                        source="easyone",
                        title=f"Ordine {parsed['order_number']}",
                        start_at=start_at,
                        end_at=start_at + timedelta(minutes=30),
                        description="Ordine EasyOne / joborder",
                        customer=str(customer) if customer else None,
                        color=_EASYONE_COLOR,
                    )
                )

            if len(headers) < _PAGE_SIZE:
                break
            skip += len(headers)

        return events

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, date):
            return datetime.combine(value, time.min, tzinfo=UTC)
        text = str(value).strip()
        if not text:
            return None
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
        try:
            parsed_date = date.fromisoformat(text[:10])
            return datetime.combine(parsed_date, time(hour=9), tzinfo=UTC)
        except ValueError:
            return None
