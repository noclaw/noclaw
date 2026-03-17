"""
CLI wrapper for Slack integration.

Usage:
    python query.py channels
    python query.py messages <channel> [--hours N]
    python query.py send <channel> <message>
    python query.py check [--hours N]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add the scripts directory to Python path for integration imports
SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


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


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Slack Integration")
    parser.add_argument("action", choices=["channels", "messages", "send", "check"])
    parser.add_argument("channel", nargs="?", default=None)
    parser.add_argument("message", nargs="?", default=None)
    parser.add_argument("--hours", type=int, default=2)

    args = parser.parse_args()

    try:
        cmd_slack(args)
    except Exception as e:
        print(json.dumps({"error": str(e), "type": "runtime"}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
