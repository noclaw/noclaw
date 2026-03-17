#!/usr/bin/env python3
"""
Context Manager - Handles channel tracking, message history, and persistence.

Single-user system. The `channel` field identifies where messages come from
(e.g., "api", "telegram_12345", "slack_U042VNB1G") — not different users.
"""

import sqlite3
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# History configuration
MAX_RECENT_HISTORY = 10
ARCHIVE_THRESHOLD = 50  # Archive history when it exceeds this


class ContextManager:
    """Manages channel tracking, message history, and shared workspace."""

    def __init__(self, db_path: Path, workspace_dir: Path = None):
        self.db_path = db_path
        self.workspace_dir = workspace_dir or Path("workspace")
        self.init_database()

    def init_database(self):
        """Initialize SQLite database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Channels table — tracks which channels have been seen
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    channel TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Message history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message TEXT NOT NULL,
                    response TEXT,
                    model_used TEXT,
                    tokens_used INTEGER,
                    metadata TEXT,
                    FOREIGN KEY (channel) REFERENCES channels (channel)
                )
            """)


            conn.commit()
            logger.info("Database schema initialized")

    def ensure_channel(self, channel: str) -> None:
        """Ensure a channel exists in the database and update last_active."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO channels (channel) VALUES (?)
                ON CONFLICT(channel) DO UPDATE SET last_active = CURRENT_TIMESTAMP
            """, (channel,))
            conn.commit()

    def add_message(self, channel: str, message: str, response: str, metadata: Dict = None,
                   model_used: str = None, tokens_used: int = None):
        """Add message to history and check if archival is needed"""
        self.ensure_channel(channel)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO message_history (channel, message, response, model_used, tokens_used, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (channel, message, response, model_used, tokens_used, json.dumps(metadata or {})))
            conn.commit()

            # Check if we need to archive old history
            cursor.execute("""
                SELECT COUNT(*) FROM message_history WHERE channel = ?
            """, (channel,))
            count = cursor.fetchone()[0]

            if count > ARCHIVE_THRESHOLD:
                logger.info(f"History for {channel} exceeds threshold, archiving old messages")
                self._archive_old_history(channel, keep_recent=MAX_RECENT_HISTORY)

    def get_history(self, channel: str, limit: int = 10) -> List[Dict]:
        """
        Get message history for a channel (newest-first).

        Returns messages ordered by newest first. When displaying chronologically,
        remember to reverse() the list.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM message_history
                WHERE channel = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
            """, (channel, limit))

            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            return [
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "message": row["message"],
                    "response": row["response"],
                    "model_used": row["model_used"] if "model_used" in columns else None,
                    "tokens_used": row["tokens_used"] if "tokens_used" in columns else None,
                    "metadata": json.loads(row["metadata"] or "{}")
                }
                for row in rows
            ]

    def _archive_old_history(self, channel: str, keep_recent: int = MAX_RECENT_HISTORY):
        """
        Archive old conversation history to a file and remove from database.

        Keeps only the most recent N messages in the database for performance.
        Older messages are saved to workspace/conversations/ for reference.
        """
        conversations_dir = self.workspace_dir / "conversations"
        conversations_dir.mkdir(exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM message_history
                WHERE channel = ?
                ORDER BY timestamp DESC
            """, (channel,))

            all_messages = [dict(row) for row in cursor.fetchall()]

            if len(all_messages) <= keep_recent:
                return

            messages_to_keep = all_messages[:keep_recent]
            messages_to_archive = all_messages[keep_recent:]

            if not messages_to_archive:
                return

            archive_date = datetime.datetime.now(datetime.UTC)
            archive_file = conversations_dir / f"archive_{archive_date}.json"

            archive_data = {
                "channel": channel,
                "archived_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "message_count": len(messages_to_archive),
                "messages": messages_to_archive
            }

            archive_file.write_text(json.dumps(archive_data, indent=2))
            logger.info(
                f"Archived {len(messages_to_archive)} messages to {archive_file.name}"
            )

            ids_to_delete = [msg["id"] for msg in messages_to_archive]

            placeholders = ",".join("?" * len(ids_to_delete))
            cursor.execute(f"""
                DELETE FROM message_history
                WHERE id IN ({placeholders})
            """, ids_to_delete)

            conn.commit()
            logger.info(f"Removed {len(ids_to_delete)} archived messages from database")

    def get_archived_conversations(self, channel: str) -> List[Dict]:
        """Get list of archived conversation files"""
        conversations_dir = self.workspace_dir / "conversations"

        if not conversations_dir.exists():
            return []

        archives = []
        for archive_file in sorted(conversations_dir.glob("archive_*.json"), reverse=True):
            try:
                data = json.loads(archive_file.read_text())
                archives.append({
                    "filename": archive_file.name,
                    "archived_at": data.get("archived_at"),
                    "message_count": data.get("message_count"),
                    "path": str(archive_file)
                })
            except Exception as e:
                logger.error(f"Error reading archive {archive_file}: {e}")

        return archives

    def list_channels(self) -> List[Dict]:
        """List all channels with message counts, ordered by last active."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.channel, c.created_at, c.last_active,
                       COUNT(m.id) as message_count
                FROM channels c
                LEFT JOIN message_history m ON c.channel = m.channel
                GROUP BY c.channel
                ORDER BY c.last_active DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_default_claude_md(self) -> str:
        """Get default CLAUDE.md content"""
        return f"""# Personal Assistant

You are a personal AI assistant.

## Guidelines
- Be helpful and concise
- Focus on practical solutions
- Conversation history (last {MAX_RECENT_HISTORY} exchanges) is provided automatically
- Suggest task scheduling when appropriate

## Progress Updates
For multi-step or long-running tasks, append brief status lines to your progress file:
```bash
echo "Searching emails for urgent items" >> .progress/$AGENT_ID.log
```
Use `$AGENT_ID` from your environment. One short line per meaningful milestone — not every tool call.

## Complex Tasks
When interacting with external systems (browsers, GUIs, APIs, tmux sessions):
- **Observe first** — check current state before acting
- **One action at a time** — don't chain multiple actions blindly
- **Verify after acting** — confirm the action worked before moving on
- **Recover from failures** — if something fails, observe again and adjust

## Time Management
- If you've been working for more than 5 minutes, wrap up and deliver what you have
- Partial results are better than no results — summarize progress and what remains
- For scheduled tasks, respect the time budget even more strictly

## Cleanup
When your task is complete, clean up after yourself:
- Kill any tmux sessions you created
- Close any browser tabs you opened via agent-browser
- Remove temp files you created in /tmp
- Kill background processes you spawned that are no longer needed
- Leave the system as you found it

## User Workspace
Your workspace is the current directory with:
- `CLAUDE.md` - Your instructions (this file)
- `conversations/` - Archived conversation history (when enabled)

## Tasks
Reusable tasks are defined as markdown files in `.claude/tasks/`.
Scheduled tasks run automatically via the heartbeat. On-demand tasks can be
triggered via the API or by asking through a channel.
See `TASK-TEMPLATE.md` in the tasks directory for the recommended format.
"""
