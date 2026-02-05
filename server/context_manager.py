#!/usr/bin/env python3
"""
Context Manager - Handles user contexts and persistence
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


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
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                workspace_path = str(Path("data/workspaces") / user_id)
                claude_md = self._get_default_claude_md(user_id)

                cursor.execute("""
                    INSERT INTO contexts (user_id, workspace_path, claude_md, settings)
                    VALUES (?, ?, ?, ?)
                """, (user_id, workspace_path, claude_md, "{}"))
                conn.commit()

                # Create workspace directory
                Path(workspace_path).mkdir(parents=True, exist_ok=True)

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

    def add_message(self, user_id: str, message: str, response: str, metadata: Dict = None):
        """Add message to history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO message_history (user_id, message, response, metadata)
                VALUES (?, ?, ?, ?)
            """, (user_id, message, response, json.dumps(metadata or {})))
            conn.commit()

    def get_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get message history for user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM message_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))

            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "message": row["message"],
                    "response": row["response"],
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

    def _get_default_claude_md(self, user_id: str) -> str:
        """Get default CLAUDE.md content for new user"""
        return f"""# Personal Assistant Context for {user_id}

You are a personal AI assistant helping {user_id} with various tasks.

## Guidelines
- Be helpful and concise
- Focus on practical solutions
- Remember context between conversations
- Suggest task scheduling when appropriate

## User Workspace
Your workspace is mounted at /workspace
You can read and write files as needed for the user's tasks.

## Scheduling
If the user asks you to remind them or do something at a specific time,
you can suggest creating a scheduled task.
"""