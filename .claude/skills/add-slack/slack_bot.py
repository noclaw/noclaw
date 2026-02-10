#!/usr/bin/env python3
"""
Slack Bot for NoClaw

Provides Slack chat interface to your personal AI assistant.
Uses Socket Mode (no public URL needed).
"""

import os
import re
import logging
import asyncio
from pathlib import Path

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

logger = logging.getLogger(__name__)


class SlackBot:
    """Slack bot that connects to NoClaw assistant"""

    def __init__(self, assistant, bot_token: str, app_token: str, allowed_users: list):
        """
        Initialize Slack bot

        Args:
            assistant: Reference to PersonalAssistant
            bot_token: Slack bot token (xoxb-...)
            app_token: Slack app-level token (xapp-...) for Socket Mode
            allowed_users: List of allowed Slack user IDs (U...)
        """
        self.assistant = assistant
        self.bot_token = bot_token
        self.app_token = app_token
        self.allowed_users = list(allowed_users)
        self.app = None
        self.handler = None
        self._task = None

        logger.info(f"Slack bot initialized for {len(allowed_users)} users")

    async def start(self):
        """Start the Slack bot in Socket Mode"""
        self.app = AsyncApp(token=self.bot_token)

        # Register event handlers
        self._register_handlers()

        # Start Socket Mode
        self.handler = AsyncSocketModeHandler(self.app, self.app_token)
        self._task = asyncio.create_task(self.handler.start_async())

        logger.info("Slack bot started (Socket Mode)")

    async def stop(self):
        """Stop the Slack bot"""
        if self.handler:
            await self.handler.close_async()
        if self._task:
            self._task.cancel()
        logger.info("Slack bot stopped")

    def _register_handlers(self):
        """Register all Slack event handlers"""

        @self.app.event("message")
        async def handle_message_event(event, say):
            # Only handle DMs, ignore bot messages and subtypes (edits, joins, etc.)
            if event.get("channel_type") != "im":
                return
            if event.get("bot_id") or event.get("subtype"):
                return

            user_id = event.get("user")
            text = event.get("text", "")

            if not self.is_authorized(user_id):
                await say("Unauthorized. Contact bot admin.")
                logger.warning(f"Unauthorized Slack access attempt from {user_id}")
                return

            # Handle message-based commands
            lower = text.strip().lower()
            if lower in ("help", "/help"):
                await say(self._help_text())
                return
            elif lower in ("status", "/status"):
                await say(self._status_text(user_id))
                return
            elif lower in ("memory", "/memory"):
                await say(self._memory_text(user_id))
                return
            elif lower in ("forget", "/forget"):
                self._do_forget(user_id)
                await say("Memory cleared!")
                return

            # Handle file uploads
            files = event.get("files", [])
            if files:
                text = await self._handle_file(user_id, files[0], text)

            # Process with assistant
            await self._process_and_reply(user_id, text, say)

        @self.app.event("app_mention")
        async def handle_mention(event, say):
            user_id = event.get("user")
            text = event.get("text", "")

            if not self.is_authorized(user_id):
                await say("Unauthorized. Contact bot admin.")
                return

            # Strip the bot mention from the text
            text = re.sub(r'<@[A-Za-z0-9]+>\s*', '', text).strip()

            if not text:
                await say("How can I help? Send me a message!")
                return

            # Reply in thread to keep channels clean
            await self._process_and_reply(
                user_id, text, say,
                thread_ts=event.get("ts")
            )

    def is_authorized(self, user_id: str) -> bool:
        """Check if user is authorized"""
        if not self.allowed_users:
            return True
        return user_id in self.allowed_users

    def get_user_id(self, slack_id: str) -> str:
        """Map Slack ID to NoClaw user ID"""
        return f"slack_{slack_id}"

    async def _process_and_reply(self, slack_user_id, text, say, thread_ts=None):
        """Process message through assistant and reply"""
        noclaw_user = self.get_user_id(slack_user_id)
        logger.info(f"Message from {noclaw_user}: {text[:50]}...")

        try:
            result = await self.assistant.process_message(
                user=noclaw_user,
                message=text,
                model_hint=os.getenv("SLACK_MODEL_HINT", "sonnet")
            )

            response = result.get("response", "Sorry, I couldn't process that.")

            # Chunk long messages for readability
            if len(response) > 3000:
                chunks = [response[i:i+3000] for i in range(0, len(response), 3000)]
                for chunk in chunks:
                    await say(chunk, thread_ts=thread_ts)
            else:
                await say(response, thread_ts=thread_ts)

        except Exception as e:
            logger.error(f"Error processing Slack message: {e}")
            await say(f"Error: {str(e)}", thread_ts=thread_ts)

    async def _handle_file(self, slack_user_id, file_info, caption):
        """Download file to workspace and return enhanced message text"""
        noclaw_user = self.get_user_id(slack_user_id)
        file_name = file_info.get("name", "uploaded_file")
        file_url = file_info.get("url_private_download")

        if not file_url:
            return caption or "File received but could not be downloaded"

        try:
            user_context = self.assistant.context_manager.get_user_context(noclaw_user)
            workspace = Path(user_context["workspace_path"])
            files_dir = workspace / "files"
            files_dir.mkdir(exist_ok=True)

            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    file_url,
                    headers={"Authorization": f"Bearer {self.bot_token}"}
                )
                file_path = files_dir / file_name
                file_path.write_bytes(resp.content)

            logger.info(f"Downloaded file from {noclaw_user}: {file_name}")
            return f"File saved: {file_name}\n\n{caption or 'Please review this file'}"

        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return caption or "File received but download failed"

    def _help_text(self):
        """Generate help text"""
        return (
            "*NoClaw AI Assistant*\n\n"
            "*Commands* (type in DM or after @mention):\n"
            "- `help` - Show this message\n"
            "- `status` - Check bot status\n"
            "- `memory` - View remembered facts\n"
            "- `forget` - Clear memory\n\n"
            "*Usage:*\n"
            "- DM me directly with any message\n"
            "- @mention me in a channel\n"
            "- Upload files in our DM for analysis\n\n"
            "*Tips:*\n"
            "- Be specific in your requests\n"
            "- I remember our conversation\n"
            "- I can help with tasks, coding, questions, etc."
        )

    def _status_text(self, slack_user_id):
        """Generate status text for user"""
        noclaw_user = self.get_user_id(slack_user_id)
        user_context = self.assistant.context_manager.get_user_context(noclaw_user)
        history = self.assistant.context_manager.get_history(noclaw_user, limit=100)

        return (
            "*Bot Status*\n\n"
            "Online and ready\n\n"
            f"*Your Stats:*\n"
            f"- Messages: {len(history)} in history\n"
            f"- Workspace: {user_context['workspace_path']}\n"
            f"- Last active: {user_context.get('last_active', 'Unknown')}\n\n"
            "*System:*\n"
            "- Model: Auto-select (Haiku/Sonnet/Opus)\n"
            "- Container: Isolated execution\n"
            "- Memory: Persistent"
        )

    def _memory_text(self, slack_user_id):
        """Generate memory text for user"""
        noclaw_user = self.get_user_id(slack_user_id)
        memory = self.assistant.context_manager.get_memory(noclaw_user)

        if len(memory.strip()) <= 50:
            return "Memory is empty. I'll remember facts as we chat!"

        if len(memory) > 3000:
            memory = memory[:3000] + "\n\n... (truncated)"
        return f"*Memory:*\n\n{memory}"

    def _do_forget(self, slack_user_id):
        """Clear memory for user"""
        noclaw_user = self.get_user_id(slack_user_id)
        self.assistant.context_manager.clear_memory(noclaw_user)

    async def send_message(self, channel_or_user_id, message):
        """Send message to channel or user (for heartbeat notifications)"""
        if self.app:
            try:
                await self.app.client.chat_postMessage(
                    channel=channel_or_user_id,
                    text=message
                )
                logger.info(f"Sent Slack notification to {channel_or_user_id}")
            except Exception as e:
                logger.error(f"Failed to send Slack message: {e}")


async def main():
    """Test the bot locally"""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    users = [u.strip() for u in os.getenv("SLACK_USER_ID", "").split(",") if u.strip()]

    if not bot_token or not app_token:
        print("Error: SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set")
        sys.exit(1)

    class MockAssistant:
        class context_manager:
            @staticmethod
            def get_user_context(uid):
                return {"workspace_path": "/tmp", "last_active": "now"}
            @staticmethod
            def get_history(uid, limit=10):
                return []
            @staticmethod
            def get_memory(uid):
                return ""
            @staticmethod
            def clear_memory(uid):
                pass

        async def process_message(self, user, message, model_hint=None):
            return {"response": f"Echo: {message}"}

    bot = SlackBot(MockAssistant(), bot_token, app_token, users)
    await bot.start()

    print("Bot started! Send a DM to your bot in Slack to test.")
    print("Press Ctrl+C to stop")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping bot...")
        await bot.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
