#!/usr/bin/env python3
"""
Context Manager - Handles user contexts, memory, and persistence
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# Memory and history configuration
MAX_RECENT_HISTORY = 10  # Increased from 5 to 10
ARCHIVE_THRESHOLD = 50  # Archive history when it exceeds this


class ContextManager:
    """Manages user contexts and message history"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # User contexts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contexts (
                    user_id TEXT PRIMARY KEY,
                    workspace_path TEXT,
                    claude_md TEXT,
                    settings TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    heartbeat_enabled INTEGER DEFAULT 0,
                    heartbeat_interval INTEGER DEFAULT 1800,
                    last_heartbeat TIMESTAMP
                )
            """)

            # Message history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message TEXT NOT NULL,
                    response TEXT,
                    model_used TEXT,
                    tokens_used INTEGER,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES contexts (user_id)
                )
            """)

            # Scheduled tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    cron_expression TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    description TEXT,
                    callback_url TEXT,
                    next_run TIMESTAMP,
                    last_run TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES contexts (user_id)
                )
            """)

            # Heartbeat log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS heartbeat_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    result TEXT,
                    checks_run TEXT,
                    FOREIGN KEY (user_id) REFERENCES contexts (user_id)
                )
            """)

            conn.commit()
            logger.info("Database schema initialized")

    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get or create user context"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Try to get existing context
            cursor.execute("""
                SELECT * FROM contexts WHERE user_id = ?
            """, (user_id,))

            row = cursor.fetchone()

            if row:
                # Update last active
                cursor.execute("""
                    UPDATE contexts
                    SET last_active = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()

                return {
                    "user_id": row["user_id"],
                    "workspace_path": row["workspace_path"],
                    "claude_md": row["claude_md"] or "",
                    "settings": json.loads(row["settings"] or "{}"),
                    "last_active": row["last_active"]
                }
            else:
                # Create new context
                workspace_path = str((Path("data/workspaces") / user_id).absolute())
                claude_md = self._get_default_claude_md(user_id)

                cursor.execute("""
                    INSERT INTO contexts (user_id, workspace_path, claude_md, settings)
                    VALUES (?, ?, ?, ?)
                """, (user_id, workspace_path, claude_md, "{}"))
                conn.commit()

                # Create workspace directory structure
                workspace = Path(workspace_path)
                workspace.mkdir(parents=True, exist_ok=True)

                # Create subdirectories
                (workspace / "files").mkdir(exist_ok=True)
                (workspace / "conversations").mkdir(exist_ok=True)

                # Initialize memory.md if it doesn't exist
                memory_file = workspace / "memory.md"
                if not memory_file.exists():
                    memory_file.write_text(f"# Memory for {user_id}\n\n")

                logger.info(f"Created new context for user: {user_id}")

                return {
                    "user_id": user_id,
                    "workspace_path": workspace_path,
                    "claude_md": claude_md,
                    "settings": {},
                    "last_active": datetime.utcnow().isoformat()
                }

    def update_workspace(self, user_id: str, workspace_path: str):
        """Update user's workspace path"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE contexts
                SET workspace_path = ?, last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (workspace_path, user_id))
            conn.commit()

        logger.info(f"Updated workspace for {user_id}: {workspace_path}")

    def update_claude_md(self, user_id: str, claude_md: str):
        """Update user's CLAUDE.md instructions"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE contexts
                SET claude_md = ?, last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (claude_md, user_id))
            conn.commit()

        # Also save to file in workspace
        context = self.get_user_context(user_id)
        workspace = Path(context["workspace_path"])
        workspace.mkdir(parents=True, exist_ok=True)
        claude_file = workspace / "CLAUDE.md"
        claude_file.write_text(claude_md)

        logger.info(f"Updated CLAUDE.md for {user_id}")

    def add_message(self, user_id: str, message: str, response: str, metadata: Dict = None,
                   model_used: str = None, tokens_used: int = None):
        """Add message to history and check if archival is needed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO message_history (user_id, message, response, model_used, tokens_used, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, message, response, model_used, tokens_used, json.dumps(metadata or {})))
            conn.commit()

            # Check if we need to archive old history
            cursor.execute("""
                SELECT COUNT(*) FROM message_history WHERE user_id = ?
            """, (user_id,))
            count = cursor.fetchone()[0]

            if count > ARCHIVE_THRESHOLD:
                logger.info(f"History for {user_id} exceeds threshold, archiving old messages")
                self._archive_old_history(user_id, keep_recent=MAX_RECENT_HISTORY)

    def get_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """
        Get message history for user (newest-first).

        Returns messages ordered by newest first. When displaying chronologically,
        remember to reverse() the list.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM message_history
                WHERE user_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
            """, (user_id, limit))

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

    def add_scheduled_task(self, task: Dict) -> int:
        """Add a scheduled task"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scheduled_tasks
                (user_id, cron_expression, prompt, description, callback_url, next_run)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                task["user_id"],
                task["cron_expression"],
                task["prompt"],
                task.get("description"),
                task.get("callback_url"),
                task.get("next_run")
            ))
            conn.commit()
            return cursor.lastrowid

    def get_scheduled_tasks(self, user_id: Optional[str] = None, status: str = "active") -> List[Dict]:
        """Get scheduled tasks, optionally filtered by user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if user_id:
                cursor.execute("""
                    SELECT * FROM scheduled_tasks
                    WHERE user_id = ? AND status = ?
                    ORDER BY next_run
                """, (user_id, status))
            else:
                cursor.execute("""
                    SELECT * FROM scheduled_tasks
                    WHERE status = ?
                    ORDER BY next_run
                """, (status,))

            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def update_task_run(self, task_id: int, next_run: datetime):
        """Update task after execution"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE scheduled_tasks
                SET last_run = CURRENT_TIMESTAMP, next_run = ?
                WHERE id = ?
            """, (next_run, task_id))
            conn.commit()

    def delete_task(self, task_id: int) -> bool:
        """Delete a scheduled task"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM scheduled_tasks WHERE id = ?
            """, (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_memory(self, user_id: str) -> str:
        """Get persistent memory for user"""
        context = self.get_user_context(user_id)
        workspace = Path(context["workspace_path"])
        memory_file = workspace / "memory.md"

        if memory_file.exists():
            return memory_file.read_text()
        else:
            return f"# Memory for {user_id}\n\n"

    def append_memory(self, user_id: str, fact: str):
        """Append a fact to user's memory"""
        context = self.get_user_context(user_id)
        workspace = Path(context["workspace_path"])
        memory_file = workspace / "memory.md"

        # Ensure memory file exists
        if not memory_file.exists():
            memory_file.write_text(f"# Memory for {user_id}\n\n")

        # Append the fact with timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")
        current_content = memory_file.read_text()

        # Check if fact already exists (simple duplicate detection)
        if fact.lower() not in current_content.lower():
            memory_file.write_text(
                current_content + f"- [{timestamp}] {fact}\n"
            )
            logger.info(f"Added memory for {user_id}: {fact[:50]}...")
        else:
            logger.debug(f"Skipped duplicate memory for {user_id}")

    def remove_memory(self, user_id: str, search: str):
        """Remove memory lines matching search string (case-insensitive)"""
        context = self.get_user_context(user_id)
        workspace = Path(context["workspace_path"])
        memory_file = workspace / "memory.md"

        if not memory_file.exists():
            return

        lines = memory_file.read_text().splitlines()
        search_lower = search.lower()
        kept = [line for line in lines if search_lower not in line.lower()]

        if len(kept) < len(lines):
            memory_file.write_text("\n".join(kept) + "\n")
            removed = len(lines) - len(kept)
            logger.info(f"Removed {removed} memory line(s) for {user_id} matching: {search[:50]}")

    def clear_memory(self, user_id: str):
        """Clear user's memory (use with caution)"""
        context = self.get_user_context(user_id)
        workspace = Path(context["workspace_path"])
        memory_file = workspace / "memory.md"

        memory_file.write_text(f"# Memory for {user_id}\n\n")
        logger.info(f"Cleared memory for {user_id}")

    def _archive_old_history(self, user_id: str, keep_recent: int = MAX_RECENT_HISTORY):
        """
        Archive old conversation history to a file and remove from database.

        Keeps only the most recent N messages in the database for performance.
        Older messages are saved to workspace/conversations/ for reference.
        """
        context = self.get_user_context(user_id)
        workspace = Path(context["workspace_path"])
        conversations_dir = workspace / "conversations"
        conversations_dir.mkdir(exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get messages to archive (all except most recent N)
            cursor.execute("""
                SELECT * FROM message_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
            """, (user_id,))

            all_messages = [dict(row) for row in cursor.fetchall()]

            if len(all_messages) <= keep_recent:
                return  # Nothing to archive

            # Split into keep vs archive
            messages_to_keep = all_messages[:keep_recent]
            messages_to_archive = all_messages[keep_recent:]

            if not messages_to_archive:
                return

            # Create archive file with timestamp
            archive_date = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            archive_file = conversations_dir / f"archive_{archive_date}.json"

            # Save archived messages
            archive_data = {
                "user_id": user_id,
                "archived_at": datetime.utcnow().isoformat(),
                "message_count": len(messages_to_archive),
                "messages": messages_to_archive
            }

            archive_file.write_text(json.dumps(archive_data, indent=2))
            logger.info(
                f"Archived {len(messages_to_archive)} messages to {archive_file.name}"
            )

            # Delete archived messages from database
            # Get IDs of messages to delete
            ids_to_delete = [msg["id"] for msg in messages_to_archive]

            # Delete in batches
            placeholders = ",".join("?" * len(ids_to_delete))
            cursor.execute(f"""
                DELETE FROM message_history
                WHERE id IN ({placeholders})
            """, ids_to_delete)

            conn.commit()
            logger.info(f"Removed {len(ids_to_delete)} archived messages from database")

    def get_archived_conversations(self, user_id: str) -> List[Dict]:
        """Get list of archived conversation files for user"""
        context = self.get_user_context(user_id)
        workspace = Path(context["workspace_path"])
        conversations_dir = workspace / "conversations"

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

    def _get_default_claude_md(self, user_id: str) -> str:
        """Get default CLAUDE.md content for new user"""
        return f"""# Personal Assistant Context for {user_id}

You are a personal AI assistant helping {user_id} with various tasks.

## Guidelines
- Be helpful and concise
- Focus on practical solutions
- Remember context between conversations
- Suggest task scheduling when appropriate

## Memory System
You have a persistent memory managed through special markers in your response.
Do NOT use file tools to write to memory.md — the system handles it automatically.

To save a fact, include this exact format on its own line:
REMEMBER: <fact>

To correct a fact, FORGET the old one then REMEMBER the new one:
FORGET: <search text that matches the old fact>
REMEMBER: <corrected fact>

Example — saving:
REMEMBER: User's name is Alice

Example — correcting:
FORGET: name is Alice
REMEMBER: User's name is Bob

Rules:
- You MUST include the REMEMBER:/FORGET: lines in your response for memory to be saved
- Simply saying "I'll remember that" does NOT save anything — the marker is required
- One fact per REMEMBER: line
- Don't duplicate facts already in your Remembered Facts section
- Conversation history (last {MAX_RECENT_HISTORY} exchanges) is provided automatically

## What to Remember
Use REMEMBER: when you learn:
- User preferences and habits
- Project names and details
- Important dates or deadlines
- Recurring needs or requests
- Names of people, teams, or systems

## User Workspace
Your workspace is mounted at /workspace with:
- `CLAUDE.md` - Your instructions (this file)
- `memory.md` - Persistent facts you've learned
- `files/` - User's files
- `conversations/` - Archived conversation history

## Scheduling
If the user asks you to remind them or do something at a specific time,
you can suggest creating a scheduled task.
"""