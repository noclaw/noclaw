#!/usr/bin/env python3
"""
Heartbeat Scheduler - Simple periodic checks for the AI assistant

Unlike cron (exact times, isolated), heartbeat runs periodically in the main
session and can check multiple things in one turn efficiently.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional
import time

logger = logging.getLogger(__name__)


class HeartbeatScheduler:
    """
    Simple heartbeat scheduler that runs periodic checks.

    Benefits over cron:
    - Simpler (no cron syntax)
    - More cost-effective (one turn checks multiple things)
    - Context-aware (maintains conversation memory)
    - Smart suppression (HEARTBEAT_OK if nothing important)
    """

    def __init__(self, assistant, default_interval: int = 1800):
        """
        Initialize heartbeat scheduler.

        Args:
            assistant: Reference to PersonalAssistant
            default_interval: Default check interval in seconds (default: 1800 = 30min)
        """
        self.assistant = assistant
        self.default_interval = default_interval
        self.running = False
        self.task = None

        logger.info(f"Heartbeat scheduler initialized (interval: {default_interval}s)")

    async def start(self):
        """Start the heartbeat scheduler"""
        if self.running:
            logger.warning("Heartbeat scheduler already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        logger.info("Heartbeat scheduler started")

    async def stop(self):
        """Stop the heartbeat scheduler"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat scheduler stopped")

    async def _run_loop(self):
        """Main heartbeat loop"""
        logger.info("Heartbeat loop started")

        while self.running:
            try:
                # Get all users with heartbeat enabled
                users_to_check = self._get_users_for_heartbeat()

                for user_id, interval in users_to_check:
                    try:
                        await self._run_heartbeat_for_user(user_id)
                    except Exception as e:
                        logger.error(f"Heartbeat failed for {user_id}: {e}")

                # Sleep until next check (use shortest interval)
                sleep_time = min(
                    [interval for _, interval in users_to_check],
                    default=self.default_interval
                )
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                logger.info("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(60)  # Back off on error

    def _get_users_for_heartbeat(self) -> list:
        """
        Get users who have heartbeat enabled and are due for a check.

        Returns:
            List of (user_id, interval) tuples
        """
        import sqlite3

        users = []
        try:
            with sqlite3.connect(self.assistant.context_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT user_id, heartbeat_enabled, heartbeat_interval, last_heartbeat
                    FROM contexts
                    WHERE heartbeat_enabled = 1
                """)

                now = datetime.now(timezone.utc)

                for row in cursor.fetchall():
                    user_id = row["user_id"]
                    interval = row["heartbeat_interval"] or self.default_interval
                    last_heartbeat = row["last_heartbeat"]

                    # Check if it's time for a heartbeat
                    if last_heartbeat:
                        last_check = datetime.fromisoformat(last_heartbeat.replace("Z", "+00:00"))
                        next_check = last_check + timedelta(seconds=interval)

                        if now >= next_check:
                            users.append((user_id, interval))
                    else:
                        # First heartbeat
                        users.append((user_id, interval))

        except Exception as e:
            logger.error(f"Error getting users for heartbeat: {e}")

        return users

    async def _run_heartbeat_for_user(self, user_id: str):
        """
        Run heartbeat check for a specific user.

        Reads HEARTBEAT.md from user's workspace and executes check.
        """
        logger.info(f"Running heartbeat for user: {user_id}")

        # Get user context
        context = self.assistant.context_manager.get_user_context(user_id)
        workspace = Path(context["workspace_path"])
        heartbeat_file = workspace / "HEARTBEAT.md"

        # Check if HEARTBEAT.md exists
        if not heartbeat_file.exists():
            logger.debug(f"No HEARTBEAT.md for {user_id}, creating default")
            self._create_default_heartbeat(user_id, heartbeat_file)

        # Read heartbeat checklist
        checklist = heartbeat_file.read_text()

        # Build heartbeat prompt
        prompt = f"""[HEARTBEAT CHECK]

Review the checklist below and check if anything needs attention:

{checklist}

If nothing needs attention, respond with exactly: HEARTBEAT_OK

If something needs attention, briefly describe what and why.
Keep it concise (1-2 sentences max).
"""

        try:
            # Run with Haiku for cost efficiency
            result = await self.assistant.process_message(
                user=user_id,
                message=prompt,
                model_hint="haiku"  # Use Haiku for heartbeats
            )

            response = result.get("response", "")

            # Log heartbeat result
            self._log_heartbeat(user_id, response)

            # Update last heartbeat time
            self._update_last_heartbeat(user_id)

            # Check if action needed
            if "HEARTBEAT_OK" in response:
                logger.info(f"Heartbeat OK for {user_id}")
            else:
                logger.info(f"Heartbeat alert for {user_id}: {response[:100]}")
                # Note: In a real implementation, you might want to send a notification here
                # For now, the response is just logged

        except Exception as e:
            logger.error(f"Error running heartbeat for {user_id}: {e}")

    def _create_default_heartbeat(self, user_id: str, heartbeat_file: Path):
        """Create default HEARTBEAT.md file"""
        default_content = f"""# Heartbeat Checklist for {user_id}

This checklist is reviewed every heartbeat (default: 30 minutes).

## Checks

- [ ] Any urgent messages or notifications?
- [ ] Any tasks due soon?
- [ ] Any errors or issues that need attention?

## Instructions

Only respond if something genuinely needs attention.
Otherwise, respond with: HEARTBEAT_OK

Keep responses brief and actionable.
"""
        heartbeat_file.write_text(default_content)
        logger.info(f"Created default HEARTBEAT.md for {user_id}")

    def _log_heartbeat(self, user_id: str, result: str):
        """Log heartbeat result to database"""
        import sqlite3
        import json

        try:
            with sqlite3.connect(self.assistant.context_manager.db_path) as conn:
                cursor = conn.cursor()

                # Store in heartbeat_log table
                cursor.execute("""
                    INSERT INTO heartbeat_log (user_id, result, checks_run)
                    VALUES (?, ?, ?)
                """, (user_id, result, json.dumps({"default": True})))

                conn.commit()

        except Exception as e:
            logger.error(f"Error logging heartbeat: {e}")

    def _update_last_heartbeat(self, user_id: str):
        """Update last heartbeat timestamp"""
        import sqlite3

        try:
            with sqlite3.connect(self.assistant.context_manager.db_path) as conn:
                cursor = conn.cursor()

                now = datetime.now(timezone.utc).isoformat()

                cursor.execute("""
                    UPDATE contexts
                    SET last_heartbeat = ?
                    WHERE user_id = ?
                """, (now, user_id))

                conn.commit()

        except Exception as e:
            logger.error(f"Error updating last heartbeat: {e}")

    def enable_for_user(self, user_id: str, interval: Optional[int] = None):
        """Enable heartbeat for a user"""
        import sqlite3

        interval = interval or self.default_interval

        try:
            with sqlite3.connect(self.assistant.context_manager.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE contexts
                    SET heartbeat_enabled = 1,
                        heartbeat_interval = ?
                    WHERE user_id = ?
                """, (interval, user_id))

                conn.commit()

            logger.info(f"Enabled heartbeat for {user_id} (interval: {interval}s)")

        except Exception as e:
            logger.error(f"Error enabling heartbeat: {e}")

    def disable_for_user(self, user_id: str):
        """Disable heartbeat for a user"""
        import sqlite3

        try:
            with sqlite3.connect(self.assistant.context_manager.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE contexts
                    SET heartbeat_enabled = 0
                    WHERE user_id = ?
                """, (user_id,))

                conn.commit()

            logger.info(f"Disabled heartbeat for {user_id}")

        except Exception as e:
            logger.error(f"Error disabling heartbeat: {e}")


if __name__ == "__main__":
    # Simple test
    print("Heartbeat Scheduler")
    print("=" * 60)
    print("\nThis module implements simple periodic checks.")
    print("\nKey features:")
    print("  - Runs every 30 minutes (configurable)")
    print("  - Reads HEARTBEAT.md checklist")
    print("  - Returns HEARTBEAT_OK if nothing needs attention")
    print("  - Uses Haiku model for cost efficiency")
    print("  - Context-aware (maintains conversation memory)")
    print("\nMuch simpler than cron!")
