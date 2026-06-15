from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.core.exceptions import CalendarError, MailError
from app.integrations.calendar import outlook_calendar
from app.integrations.easyone.calendar_client import EasyOneCalendarClient
from app.integrations.easyone.context import build_easyone_client
from app.repositories.mail_repo import MailAccountRepository
from app.schemas.calendar import CalendarEvent, CalendarStatusResponse, UnifiedCalendarResponse
from app.services.mail_service import MailService


class CalendarService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.mail_repo = MailAccountRepository(session)

    def status(
        self,
        *,
        easyone_user_id: str,
        easyone_access_token: str | None = None,
    ) -> CalendarStatusResponse:
        outlook_account = self._first_outlook_account(easyone_user_id)
        easyone_connected = bool(
            self.settings.easyone_base_url
            and self.settings.easyone_mode in ("http", "hybrid")
            and easyone_access_token
        )
        needs_reconnect = False
        if outlook_account:
            mail_service = MailService(self.session, self.settings)
            try:
                mail_service._ensure_access_token(outlook_account)
            except MailError:
                needs_reconnect = True

        portal = (self.settings.easyone_portal_url or "").strip()
        return CalendarStatusResponse(
            easyone_configured=bool(self.settings.easyone_base_url),
            easyone_connected=easyone_connected,
            easyone_portal_url=portal or None,
            outlook_configured=self.settings.microsoft_oauth_configured,
            outlook_account_available=outlook_account is not None,
            outlook_account_id=outlook_account.id if outlook_account else None,
            outlook_email=outlook_account.email_address if outlook_account else None,
            needs_outlook_reconnect=needs_reconnect,
        )

    def unified(
        self,
        *,
        easyone_user_id: str,
        easyone_access_token: str | None,
        start: datetime | None = None,
        end: datetime | None = None,
        outlook_account_id: uuid.UUID | None = None,
        include_outlook: bool = True,
        include_easyone: bool = True,
    ) -> UnifiedCalendarResponse:
        now = datetime.now(UTC)
        range_start = start or (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        range_end = end or (range_start + timedelta(days=7))
        if range_end <= range_start:
            range_end = range_start + timedelta(days=7)

        events: list[CalendarEvent] = []
        warnings: list[str] = []
        outlook_count = 0
        easyone_count = 0
        outlook_connected = False
        easyone_connected = False

        if include_easyone:
            if not easyone_access_token:
                warnings.append(
                    "EasyOne: effettuare l'accesso all'applicazione per caricare l'agenda CRM."
                )
            else:
                http = build_easyone_client(self.settings, access_token=easyone_access_token)
                if http:
                    easyone_connected = True
                    eo_events, eo_warnings = EasyOneCalendarClient(http).list_events(
                        start=range_start,
                        end=range_end,
                    )
                    events.extend(eo_events)
                    easyone_count = len(eo_events)
                    warnings.extend(eo_warnings)
                else:
                    warnings.append("EasyOne non configurato nel servizio locale.")

        if include_outlook:
            account = self._resolve_outlook_account(easyone_user_id, outlook_account_id)
            if account:
                mail_service = MailService(self.session, self.settings)
                token = mail_service._ensure_access_token(account)
                try:
                    ol_events = outlook_calendar.list_events(
                        token,
                        start=range_start,
                        end=range_end,
                    )
                    events.extend(ol_events)
                    outlook_count = len(ol_events)
                    outlook_connected = True
                except CalendarError as exc:
                    warnings.append(str(exc))
            else:
                warnings.append(
                    "Outlook non collegato. Usare la scheda Posta → Accedi con Outlook."
                )

        events.sort(key=lambda item: item.start_at)
        return UnifiedCalendarResponse(
            start=range_start,
            end=range_end,
            events=events,
            outlook_count=outlook_count,
            easyone_count=easyone_count,
            outlook_connected=outlook_connected,
            easyone_connected=easyone_connected,
            warnings=warnings,
        )

    def _first_outlook_account(self, easyone_user_id: str):
        for account in self.mail_repo.list_for_user(easyone_user_id):
            if account.provider == "outlook":
                return account
        return None

    def _resolve_outlook_account(
        self,
        easyone_user_id: str,
        outlook_account_id: uuid.UUID | None,
    ):
        if outlook_account_id:
            account = self.mail_repo.get_for_user(outlook_account_id, easyone_user_id)
            if account and account.provider == "outlook":
                return account
            return None
        return self._first_outlook_account(easyone_user_id)
