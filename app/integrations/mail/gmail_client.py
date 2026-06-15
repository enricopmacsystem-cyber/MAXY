from __future__ import annotations

import base64
import re
from datetime import UTC, datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime

import httpx

from app.core.exceptions import MailError
from app.schemas.mail import (
    MailAttachmentInput,
    MailMessageDetail,
    MailMessageSummary,
)

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


def list_messages(access_token: str, *, limit: int = 50, folder: str = "inbox") -> list[MailMessageSummary]:
    label = "INBOX" if folder.lower() == "inbox" else folder.upper()
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"maxResults": min(limit, 100), "labelIds": label}
    with httpx.Client(timeout=30.0) as client:
        response = client.get(f"{GMAIL_API}/messages", headers=headers, params=params)
        if response.status_code >= 400:
            raise MailError(f"Errore lettura Gmail: {response.text[:300]}")
        payload = response.json()
        summaries: list[MailMessageSummary] = []
        for item in payload.get("messages", []):
            msg_id = item.get("id")
            if not msg_id:
                continue
            detail = client.get(
                f"{GMAIL_API}/messages/{msg_id}",
                headers=headers,
                params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
            )
            if detail.status_code >= 400:
                continue
            summaries.append(_parse_metadata(detail.json()))
        return summaries


def get_message(access_token: str, message_id: str) -> MailMessageDetail:
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            f"{GMAIL_API}/messages/{message_id}",
            headers=headers,
            params={"format": "full"},
        )
    if response.status_code >= 400:
        raise MailError(f"Errore lettura messaggio Gmail: {response.text[:300]}")
    return _parse_full_message(response.json())


def send_message(
    access_token: str,
    *,
    to: str,
    subject: str,
    body: str,
    cc: list[str] | None = None,
    attachments: list[MailAttachmentInput] | None = None,
) -> str:
    mime = MIMEMultipart()
    mime["To"] = to
    mime["Subject"] = subject
    if cc:
        mime["Cc"] = ", ".join(cc)
    mime.attach(MIMEText(body, "plain", "utf-8"))
    for attachment in attachments or []:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(base64.b64decode(attachment.content_base64))
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{attachment.filename}"',
        )
        mime.attach(part)

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{GMAIL_API}/messages/send",
            headers=headers,
            json={"raw": raw},
        )
    if response.status_code >= 400:
        raise MailError(f"Invio Gmail fallito: {response.text[:300]}")
    return str(response.json().get("id", ""))


def _header_value(headers: list[dict], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return str(header.get("value", ""))
    return ""


def _parse_address(raw: str) -> tuple[str, str | None]:
    match = re.match(r'^(?:"?([^"]*)"?\s)?<?([^<>]+@[^<>]+)>?$', raw.strip())
    if not match:
        return raw, None
    name = (match.group(1) or "").strip() or None
    return match.group(2).strip(), name


def _parse_metadata(payload: dict) -> MailMessageSummary:
    headers = payload.get("payload", {}).get("headers", [])
    from_raw = _header_value(headers, "From")
    from_address, from_name = _parse_address(from_raw)
    subject = _header_value(headers, "Subject") or "(Senza oggetto)"
    date_raw = _header_value(headers, "Date")
    received_at = None
    if date_raw:
        try:
            received_at = parsedate_to_datetime(date_raw)
            if received_at.tzinfo is None:
                received_at = received_at.replace(tzinfo=UTC)
        except Exception:
            received_at = None
    labels = payload.get("labelIds", [])
    return MailMessageSummary(
        id=str(payload.get("id", "")),
        subject=subject,
        from_address=from_address,
        from_name=from_name,
        received_at=received_at,
        snippet=str(payload.get("snippet", "")),
        is_read="UNREAD" not in labels,
    )


def _parse_full_message(payload: dict) -> MailMessageDetail:
    summary = _parse_metadata(payload)
    body_text, body_html, attachment_names = _extract_parts(payload.get("payload", {}))
    return MailMessageDetail(
        id=summary.id,
        subject=summary.subject,
        from_address=summary.from_address,
        from_name=summary.from_name,
        received_at=summary.received_at,
        body_text=body_text,
        body_html=body_html,
        attachments=attachment_names,
    )


def _extract_parts(part: dict) -> tuple[str, str | None, list[str]]:
    mime_type = part.get("mimeType", "")
    body = part.get("body", {})
    data = body.get("data")
    attachments: list[str] = []
    text = ""
    html: str | None = None

    if mime_type == "text/plain" and data:
        text = base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")
    elif mime_type == "text/html" and data:
        html = base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")

    filename = part.get("filename")
    if filename:
        attachments.append(filename)

    for child in part.get("parts", []) or []:
        child_text, child_html, child_attachments = _extract_parts(child)
        if child_text and not text:
            text = child_text
        if child_html and not html:
            html = child_html
        attachments.extend(child_attachments)

    return text, html, attachments
