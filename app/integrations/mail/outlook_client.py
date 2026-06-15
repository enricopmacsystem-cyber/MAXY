from __future__ import annotations

from datetime import datetime

import httpx

from app.core.exceptions import MailError
from app.schemas.mail import (
    MailAttachmentInput,
    MailMessageDetail,
    MailMessageSummary,
)

GRAPH_API = "https://graph.microsoft.com/v1.0"


def list_messages(access_token: str, *, limit: int = 50, folder: str = "inbox") -> list[MailMessageSummary]:
    folder_segment = "inbox" if folder.lower() == "inbox" else folder
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "$top": min(limit, 100),
        "$select": "id,subject,from,receivedDateTime,bodyPreview,isRead",
        "$orderby": "receivedDateTime desc",
    }
    url = f"{GRAPH_API}/me/mailFolders/{folder_segment}/messages"
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers, params=params)
    if response.status_code >= 400:
        raise MailError(f"Errore lettura Outlook: {response.text[:300]}")
    summaries: list[MailMessageSummary] = []
    for item in response.json().get("value", []):
        from_info = (item.get("from") or {}).get("emailAddress") or {}
        received_raw = item.get("receivedDateTime")
        received_at = None
        if received_raw:
            received_at = datetime.fromisoformat(received_raw.replace("Z", "+00:00"))
        summaries.append(
            MailMessageSummary(
                id=str(item.get("id", "")),
                subject=item.get("subject") or "(Senza oggetto)",
                from_address=str(from_info.get("address", "")),
                from_name=from_info.get("name"),
                received_at=received_at,
                snippet=str(item.get("bodyPreview", "")),
                is_read=bool(item.get("isRead", True)),
            )
        )
    return summaries


def get_message(access_token: str, message_id: str) -> MailMessageDetail:
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=30.0) as client:
        response = client.get(f"{GRAPH_API}/me/messages/{message_id}", headers=headers)
    if response.status_code >= 400:
        raise MailError(f"Errore lettura messaggio Outlook: {response.text[:300]}")
    item = response.json()
    from_info = (item.get("from") or {}).get("emailAddress") or {}
    body = item.get("body") or {}
    to_addresses = [
        str((recipient.get("emailAddress") or {}).get("address", ""))
        for recipient in item.get("toRecipients", [])
        if (recipient.get("emailAddress") or {}).get("address")
    ]
    received_raw = item.get("receivedDateTime")
    received_at = None
    if received_raw:
        received_at = datetime.fromisoformat(received_raw.replace("Z", "+00:00"))
    attachments = [
        str(att.get("name", "allegato"))
        for att in item.get("attachments", [])
        if att.get("name")
    ]
    content_type = body.get("contentType", "Text")
    content = str(body.get("content", ""))
    return MailMessageDetail(
        id=str(item.get("id", "")),
        subject=item.get("subject") or "(Senza oggetto)",
        from_address=str(from_info.get("address", "")),
        from_name=from_info.get("name"),
        to_addresses=to_addresses,
        received_at=received_at,
        body_text=content if content_type.lower() == "text" else "",
        body_html=content if content_type.lower() == "html" else None,
        attachments=attachments,
    )


def send_message(
    access_token: str,
    *,
    to: str,
    subject: str,
    body: str,
    cc: list[str] | None = None,
    attachments: list[MailAttachmentInput] | None = None,
) -> str:
    message = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "toRecipients": [{"emailAddress": {"address": to}}],
    }
    if cc:
        message["ccRecipients"] = [{"emailAddress": {"address": addr}} for addr in cc]
    if attachments:
        message["attachments"] = [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": att.filename,
                "contentType": att.content_type,
                "contentBytes": att.content_base64,
            }
            for att in attachments
        ]
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{GRAPH_API}/me/sendMail",
            headers=headers,
            json={"message": message, "saveToSentItems": True},
        )
    if response.status_code >= 400:
        raise MailError(f"Invio Outlook fallito: {response.text[:300]}")
    return ""
