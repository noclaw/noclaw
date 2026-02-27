"""
Configuration for NoClaw agent scripts.

Path layout:
  SCRIPTS_DIR   = workspace/.claude/scripts/   (this file's directory)
  PROJECT_ROOT  = workspace/                   (agent workspace)
  NOCLAW_ROOT   = .                            (noclaw project root)
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# === Paths ===
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent.parent        # workspace/
NOCLAW_ROOT = PROJECT_ROOT  # Use workspace as root to avoid read-only /app
CLAUDE_DIR = PROJECT_ROOT / ".claude"

# Load environment variables from root .env first, then script-specific overrides
load_dotenv(NOCLAW_ROOT / ".env")
load_dotenv(SCRIPTS_DIR / ".env", override=True)

# Workspace file paths
MEMORY_FILE = PROJECT_ROOT / "memory.md"
CLAUDE_FILE = PROJECT_ROOT / "CLAUDE.md"

# === Owner Identity ===
#OWNER_NAME = os.getenv("OWNER_NAME", "")

# === Data Directory ===
DATA_DIR = NOCLAW_ROOT / "data"
DATABASE_PATH = DATA_DIR / "assistant.db"

# DATABASE_URL = os.getenv("DATABASE_URL", "")

# Google OAuth
GOOGLE_CREDENTIALS_FILE = NOCLAW_ROOT / "google_credentials.json"
GOOGLE_TOKEN_FILE = NOCLAW_ROOT / "google_token.json"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Slack
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "")
SLACK_OWNER_USER_ID = os.getenv("SLACK_USER_ID", "")

#SLACK_NOTIFICATION_CHANNEL = os.getenv("SLACK_NOTIFICATION_CHANNEL", "")
#SLACK_MONITORED_CHANNELS = os.getenv("SLACK_MONITORED_CHANNELS", "").split(",")

# Calendar
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "")

# === Timezone Configuration ===

TIMEZONE = os.getenv("TIMEZONE", "America/Denver")

LOCAL_TZ = ZoneInfo(TIMEZONE)


def now_local() -> datetime:
    """Return the current time in the configured timezone (HEARTBEAT_TIMEZONE)."""
    return datetime.now(LOCAL_TZ)


