"""
Interactive CLI wrapper for direct platform integrations.

Used by the direct-integrations Claude Code skill to query Gmail, Calendar,
Slack, Google Sheets, Google Docs, and Google Drive from interactive sessions.

Usage:
    python query.py gmail list --max 5
    python query.py calendar today
    python query.py slack channels
    python query.py sheets read <spreadsheet_id> [--range "Sheet1!A1:Z100"]
    python query.py docs read <document_id>
    python query.py drive find "search term" [--type spreadsheet]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add the scripts directory to Python path for integration imports
SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def cmd_gmail(args: argparse.Namespace) -> None:
    """Handle Gmail commands."""
    from integrations.gmail import (
        check_for_urgent_emails,
        format_emails_for_context,
        get_email_details,
        get_gmail_service,
        get_unread_count,
        list_emails,
    )

    if args.action == "list":
        # Default to 24h window when no query specified (recent inbox view)
        # but no time filter when searching (user wants to find old emails too)
        hours = args.hours if args.hours is not None else (None if args.query else 24)
        emails = list_emails(
            max_results=args.max,
            query=args.query or "",
            unread_only=args.unread,
            hours_ago=hours,
        )
        print(format_emails_for_context(emails))

    elif args.action == "urgent":
        urgent = check_for_urgent_emails(hours_ago=args.hours)
        if urgent:
            print(f"Found {len(urgent)} potentially urgent emails:\n")
            print(format_emails_for_context(urgent))
        else:
            print("No urgent emails found")

    elif args.action == "unread":
        count = get_unread_count()
        print(f"Unread emails: {count}")

    elif args.action == "read":
        if not args.message_id:
            print("Error: message_id required for read command")
            sys.exit(1)
        service = get_gmail_service()
        email = get_email_details(service, args.message_id, include_body=True)
        if email:
            print(f"Subject: {email.subject}")
            print(f"From: {email.sender} <{email.sender_email}>")
            print(f"Date: {email.date}")
            print(f"Labels: {', '.join(email.labels)}")
            print(f"\n{email.body or email.snippet}")
        else:
            print("Email not found")


def cmd_calendar(args: argparse.Namespace) -> None:
    """Handle Calendar commands."""
    from integrations.calendar_api import (
        check_for_upcoming_meetings,
        format_events_for_context,
        get_today_events,
        get_upcoming_events,
    )

    if args.action == "today":
        events = get_today_events()
        print(format_events_for_context(events))

    elif args.action == "upcoming":
        events = get_upcoming_events(hours_ahead=args.hours)
        print(format_events_for_context(events))

    elif args.action == "soon":
        events = check_for_upcoming_meetings(hours_ahead=4)
        print(format_events_for_context(events))


def cmd_slack(args: argparse.Namespace) -> None:
    """Handle Slack commands."""
    from integrations.slack_api import (
        check_for_important_messages,
        format_messages_for_context,
        get_channel_id,
        get_recent_messages,
        get_slack_client,
        send_notification,
    )

    if args.action == "channels":
        client = get_slack_client()
        result = client.conversations_list(types="public_channel", limit=100)
        for ch in result.get("channels", []):
            print(f"  #{ch['name']} ({ch['id']})")

    elif args.action == "messages":
        if not args.channel:
            print("Error: channel name required")
            sys.exit(1)
        ch_id = get_channel_id(args.channel)
        if not ch_id:
            print(f"Channel not found: {args.channel}")
            sys.exit(1)
        msgs = get_recent_messages(ch_id, hours_ago=args.hours, limit=20)
        print(format_messages_for_context(msgs))

    elif args.action == "send":
        if not args.channel or not args.message:
            print("Error: channel and message required")
            sys.exit(1)
        result = send_notification(args.channel, args.message)
        print(f"Sent! (ts={result['ts']})" if result else "Failed to send")

    elif args.action == "check":
        important = check_for_important_messages(hours_ago=args.hours)
        if important:
            print(f"Found {len(important)} important messages:\n")
            print(format_messages_for_context(important))
        else:
            print("No important messages found")


def cmd_sheets(args: argparse.Namespace) -> None:
    """Handle Google Sheets commands."""
    from integrations.sheets_api import (
        append_to_spreadsheet,
        format_spreadsheet_for_context,
        get_spreadsheet_info,
        read_spreadsheet,
        write_spreadsheet,
    )

    if args.action == "read":
        if not args.target_id:
            print("Error: spreadsheet_id required")
            sys.exit(1)
        data = read_spreadsheet(
            args.target_id,
            range_notation=args.range or "",
            max_rows=args.max_rows,
        )
        print(format_spreadsheet_for_context(data))

    elif args.action == "info":
        if not args.target_id:
            print("Error: spreadsheet_id required")
            sys.exit(1)
        info = get_spreadsheet_info(args.target_id)
        print(format_spreadsheet_for_context(info))

    elif args.action == "write":
        if not args.target_id or not args.values or not args.range:
            print("Error: spreadsheet_id, --range, and --values required")
            sys.exit(1)
        parsed = json.loads(args.values)
        result = write_spreadsheet(args.target_id, args.range, parsed)
        print(json.dumps(result, indent=2))

    elif args.action == "append":
        if not args.target_id or not args.values or not args.range:
            print("Error: spreadsheet_id, --range, and --values required")
            sys.exit(1)
        parsed = json.loads(args.values)
        result = append_to_spreadsheet(args.target_id, args.range, parsed)
        print(json.dumps(result, indent=2))


def cmd_docs(args: argparse.Namespace) -> None:
    """Handle Google Docs commands."""
    from integrations.docs_api import (
        format_document_for_context,
        get_document_info,
        read_document,
    )

    if args.action == "read":
        if not args.target_id:
            print("Error: document_id required")
            sys.exit(1)
        data = read_document(args.target_id)
        print(format_document_for_context(data, max_chars=args.max_chars))

    elif args.action == "info":
        if not args.target_id:
            print("Error: document_id required")
            sys.exit(1)
        data = get_document_info(args.target_id)
        char_count = len(data.body_text)
        print(f"Title: {data.title}")
        print(f"ID: {data.id}")
        print(f"URL: {data.url}")
        print(f"Content length: ~{char_count} chars")


def cmd_drive(args: argparse.Namespace) -> None:
    """Handle Google Drive commands."""
    from integrations.drive_api import (
        find_files,
        format_files_for_context,
        get_file_by_id,
        list_files,
    )

    if args.action == "find":
        if not args.query:
            print("Error: search query required")
            sys.exit(1)
        files = find_files(args.query, file_type=args.file_type, max_results=args.max)
        print(format_files_for_context(files))

    elif args.action == "list":
        files = list_files(file_type=args.file_type, max_results=args.max)
        print(format_files_for_context(files))

    elif args.action == "get":
        if not args.query:
            print("Error: file ID required")
            sys.exit(1)
        file = get_file_by_id(args.query)
        if file:
            print(format_files_for_context([file]))
        else:
            print("File not found")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Direct Platform Integrations")
    subparsers = parser.add_subparsers(dest="service", required=True)

    # Gmail
    gmail_parser = subparsers.add_parser("gmail", help="Gmail operations")
    gmail_parser.add_argument("action", choices=["list", "urgent", "unread", "read"])
    gmail_parser.add_argument("message_id", nargs="?", default=None)
    gmail_parser.add_argument("--max", type=int, default=10)
    gmail_parser.add_argument("--query", default=None)
    gmail_parser.add_argument("--hours", type=int, default=None)
    gmail_parser.add_argument("--unread", action="store_true")

    # Calendar
    cal_parser = subparsers.add_parser("calendar", help="Calendar operations")
    cal_parser.add_argument("action", choices=["today", "upcoming", "soon"])
    cal_parser.add_argument("--hours", type=int, default=24)

    # Slack
    slack_parser = subparsers.add_parser("slack", help="Slack operations")
    slack_parser.add_argument("action", choices=["channels", "messages", "send", "check"])
    slack_parser.add_argument("channel", nargs="?", default=None)
    slack_parser.add_argument("message", nargs="?", default=None)
    slack_parser.add_argument("--hours", type=int, default=2)

    # Google Sheets
    sheets_parser = subparsers.add_parser("sheets", help="Google Sheets operations")
    sheets_parser.add_argument("action", choices=["read", "info", "write", "append"])
    sheets_parser.add_argument("target_id", nargs="?", default=None, help="Spreadsheet ID")
    sheets_parser.add_argument("--range", default=None, help="A1 notation range")
    sheets_parser.add_argument("--values", default=None, help="JSON 2D array for write/append")
    sheets_parser.add_argument("--max-rows", type=int, default=500)

    # Google Docs
    docs_parser = subparsers.add_parser("docs", help="Google Docs operations")
    docs_parser.add_argument("action", choices=["read", "info"])
    docs_parser.add_argument("target_id", nargs="?", default=None, help="Document ID")
    docs_parser.add_argument("--max-chars", type=int, default=4000)

    # Google Drive
    drive_parser = subparsers.add_parser("drive", help="Google Drive operations")
    drive_parser.add_argument("action", choices=["find", "list", "get"])
    drive_parser.add_argument("query", nargs="?", default=None, help="Search term or file ID")
    drive_parser.add_argument("--type", dest="file_type", default=None,
                              choices=["spreadsheet", "document", "folder", "presentation", "pdf"])
    drive_parser.add_argument("--max", type=int, default=10)

    args = parser.parse_args()

    try:
        if args.service == "gmail":
            cmd_gmail(args)
        elif args.service == "calendar":
            cmd_calendar(args)
    #    elif args.service == "slack":
    #        cmd_slack(args)
        elif args.service == "sheets":
            cmd_sheets(args)
        elif args.service == "docs":
            cmd_docs(args)
        elif args.service == "drive":
            cmd_drive(args)
    except Exception as e:
        print(json.dumps({"error": str(e), "type": "runtime"}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
