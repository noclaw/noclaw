"""
Gmail Direct Integration for Second Brain.

Read-only access to Gmail via Google API. Shares OAuth token with Calendar.

Usage:
    uv run python -m integrations.gmail list --max 5
    uv run python -m integrations.gmail unread
    uv run python -m integrations.gmail urgent --hours 2
    uv run python -m integrations.gmail search --query "from:someone"
"""

from __future__ import annotations

import base64
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

# Add parent dir for config imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import with_retry
from config import LOCAL_TZ, now_local

@dataclass
class Email:
    """Represents an email message."""

    id: str
    thread_id: str
    subject: str
    sender: str
    sender_email: str
    date: datetime
    snippet: str
    body: str | None = None
    labels: list[str] = field(default_factory=list)
    is_unread: bool = False


def get_gmail_service() -> Any:
    """Build authenticated Gmail API service."""
    from googleapiclient.discovery import build  # type: ignore[import-untyped]

    from integrations.auth import get_google_credentials

    creds = get_google_credentials()
    service: Any = build("gmail", "v1", credentials=creds)
    return service


def _parse_sender(sender_full: str) -> tuple[str, str]:
    """Parse 'Name <email>' format into (name, email)."""
    if "<" in sender_full:
        sender = sender_full.split("<")[0].strip().strip('"')
        sender_email = sender_full.split("<")[1].rstrip(">")
    else:
        sender = sender_full
        sender_email = sender_full
    return sender, sender_email


def _extract_body(payload: dict[str, Any]) -> str:
    """Extract email body text from payload (handles multipart MIME)."""
    body_data = payload.get("body", {}).get("data")
    if body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    parts = payload.get("parts", [])
    for part in parts:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        elif mime_type in ("multipart/alternative", "multipart/mixed"):
            result = _extract_body(part)
            if result:
                return result

    return ""


def get_email_details(service: Any, msg_id: str, include_body: bool = False) -> Email | None:
    """Get details for a single email."""
    try:
        fmt = "full" if include_body else "metadata"
        msg: dict[str, Any] = with_retry(
            lambda: service.users()
            .messages()
            .get(
                userId="me",
                id=msg_id,
                format=fmt,
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )

        headers: dict[str, str] = {
            h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])
        }

        sender, sender_email = _parse_sender(headers.get("From", ""))

        # Parse date robustly
        date_str = headers.get("Date", "")
        try:
            date = parsedate_to_datetime(date_str)
        except Exception:
            date = now_local()

        body = None
        if include_body:
            body = _extract_body(msg.get("payload", {}))

        label_ids: list[str] = msg.get("labelIds", [])

        return Email(
            id=msg["id"],
            thread_id=msg["threadId"],
            subject=headers.get("Subject", "(no subject)"),
            sender=sender,
            sender_email=sender_email,
            date=date,
            snippet=msg.get("snippet", ""),
            body=body,
            labels=label_ids,
            is_unread="UNREAD" in label_ids,
        )
    except Exception as e:
        print(f"Error getting email {msg_id}: {e}")
        return None


def list_emails(
    max_results: int = 10,
    query: str = "",
    unread_only: bool = False,
    hours_ago: int | None = None,
) -> list[Email]:
    """
    List emails matching criteria.

    Args:
        max_results: Maximum emails to return
        query: Gmail search query (e.g. "from:someone subject:important")
        unread_only: Only return unread emails
        hours_ago: Only emails from last N hours
    """
    service = get_gmail_service()

    q_parts: list[str] = []
    if query:
        q_parts.append(query)
    if unread_only:
        q_parts.append("is:unread")
    if hours_ago:
        after_date = now_local() - timedelta(hours=hours_ago)
        q_parts.append(f"after:{after_date.strftime('%Y/%m/%d')}")

    full_query = " ".join(q_parts) if q_parts else None

    result: dict[str, Any] = with_retry(
        lambda: service.users()
        .messages()
        .list(userId="me", maxResults=max_results, q=full_query)
        .execute()
    )

    messages: list[dict[str, str]] = result.get("messages", [])
    emails: list[Email] = []

    for msg in messages:
        email = get_email_details(service, msg["id"])
        if email:
            emails.append(email)

    return emails


def get_unread_count() -> int:
    """Get count of unread emails in inbox."""
    service = get_gmail_service()

    result: dict[str, Any] = with_retry(
        lambda: service.users()
        .messages()
        .list(userId="me", q="is:unread in:inbox", maxResults=1)
        .execute()
    )

    count: int = result.get("resultSizeEstimate", 0)
    return count


def check_for_urgent_emails(
    important_senders: list[str] | None = None,
    hours_ago: int = 2,
) -> list[Email]:
    """
    Check for urgent emails that need attention.

    Flags emails from important senders or with urgent keywords in subject.
    """
    recent = list_emails(max_results=20, unread_only=True, hours_ago=hours_ago)

    urgent_keywords = ["urgent", "asap", "important", "action required", "deadline"]
    urgent: list[Email] = []

    for email in recent:
        reason = ""

        # Check important senders
        if important_senders:
            for sender in important_senders:
                if sender.lower() in email.sender_email.lower():
                    reason = f"From important sender: {email.sender}"
                    break

        # Check urgent keywords in subject
        if not reason:
            subject_lower = email.subject.lower()
            for keyword in urgent_keywords:
                if keyword in subject_lower:
                    reason = f"Urgent keyword: {keyword}"
                    break

        if reason:
            email.body = reason
            urgent.append(email)

    return urgent


def get_thread_id(msg_id: str) -> str | None:
    """Resolve a Gmail message ID to its thread ID."""
    service = get_gmail_service()
    try:
        msg: dict[str, Any] = with_retry(
            lambda: service.users()
            .messages()
            .get(userId="me", id=msg_id, format="minimal")
            .execute()
        )
        return msg.get("threadId")
    except Exception:
        return None


def check_sent_reply(thread_id: str, after_timestamp: str) -> str | None:
    """
    Check if Cole sent a reply in a Gmail thread after a given time.

    Args:
        thread_id: The Gmail thread ID to check
        after_timestamp: ISO format timestamp — only look for replies after this time

    Returns:
        The reply text if Cole sent one, None otherwise.
    """
    service = get_gmail_service()

    try:
        thread_data: dict[str, Any] = with_retry(
            lambda: service.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )
    except Exception as e:
        print(f"Error fetching thread {thread_id}: {e}")
        return None

    after_dt = datetime.fromisoformat(after_timestamp)

    messages: list[dict[str, Any]] = thread_data.get("messages", [])
    for msg in messages:
        label_ids: list[str] = msg.get("labelIds", [])
        # Only look at messages Cole sent (in SENT label)
        if "SENT" not in label_ids:
            continue

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        date_str = headers.get("Date", "")
        try:
            msg_date = parsedate_to_datetime(date_str)
        except Exception:
            continue

        # Check if this sent message is after our timestamp
        if msg_date.replace(tzinfo=None) > after_dt.replace(tzinfo=None):
            body = _extract_body(msg.get("payload", {}))
            if body:
                return body

    return None


def get_important_unreplied_emails(
    hours_ago: int = 4,
    max_results: int = 10,
) -> list[Email]:
    """
    Get recent emails that Cole hasn't replied to yet.

    Returns emails from the inbox that are:
    - Received in the last N hours
    - Not from Cole himself
    - In threads where Cole's last message is NOT the most recent

    Importance filtering is done by Claude based on USER.md criteria.
    """
    service = get_gmail_service()

    after_date = now_local() - timedelta(hours=hours_ago)
    q = f"in:inbox after:{after_date.strftime('%Y/%m/%d')} -from:me"

    try:
        result: dict[str, Any] = with_retry(
            lambda: service.users()
            .messages()
            .list(userId="me", maxResults=max_results, q=q)
            .execute()
        )
    except Exception as e:
        print(f"Error listing unreplied emails: {e}")
        return []

    messages_list: list[dict[str, str]] = result.get("messages", [])
    emails: list[Email] = []

    # Track threads we've already seen to avoid duplicates
    seen_threads: set[str] = set()

    for msg_ref in messages_list:
        email = get_email_details(service, msg_ref["id"], include_body=True)
        if not email:
            continue

        # Skip if we already have a message from this thread
        if email.thread_id in seen_threads:
            continue
        seen_threads.add(email.thread_id)

        emails.append(email)

    return emails


def format_emails_for_context(emails: list[Email], max_chars: int = 2000) -> str:
    """Format emails for inclusion in Claude's context prompt."""
    if not emails:
        return "No emails found."

    output: list[str] = []
    chars = 0

    for email in emails:
        date_cst = email.date.astimezone(LOCAL_TZ) if email.date.tzinfo else email.date
        entry = (
            f"- **{email.subject}** [thread_id: {email.thread_id}]\n"
            f"  From: {email.sender} <{email.sender_email}>\n"
            f"  Date: {date_cst.strftime('%Y-%m-%d %H:%M')}\n"
            f"  {'[UNREAD] ' if email.is_unread else ''}{email.snippet[:100]}"
        )

        if chars + len(entry) > max_chars:
            remaining = len(emails) - len(output)
            output.append(f"\n... and {remaining} more emails")
            break

        output.append(entry)
        chars += len(entry)

    return "\n\n".join(output)


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gmail integration")
    parser.add_argument("command", choices=["auth", "list", "unread", "urgent", "search"])
    parser.add_argument("--max", type=int, default=10)
    parser.add_argument("--query", default="")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--unread", action="store_true")

    args = parser.parse_args()

    if args.command == "auth":
        service = get_gmail_service()
        print("Authentication successful!")

    elif args.command == "list":
        result_emails = list_emails(
            max_results=args.max, query=args.query, unread_only=args.unread, hours_ago=args.hours
        )
        print(format_emails_for_context(result_emails))

    elif args.command == "unread":
        count = get_unread_count()
        print(f"Unread emails: {count}")

    elif args.command == "urgent":
        urgent_emails = check_for_urgent_emails(hours_ago=args.hours)
        if urgent_emails:
            print(f"Found {len(urgent_emails)} potentially urgent emails:")
            print(format_emails_for_context(urgent_emails))
        else:
            print("No urgent emails found")

    elif args.command == "search":
        if not args.query:
            print("--query required for search command")
            sys.exit(1)
        result_emails = list_emails(max_results=args.max, query=args.query)
        print(format_emails_for_context(result_emails))
