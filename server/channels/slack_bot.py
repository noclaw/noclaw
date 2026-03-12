"""Slack channel plugin for NoClaw."""

import os
import re
import logging
import asyncio
from pathlib import Path

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from .base import Channel

logger = logging.getLogger(__name__)


class SlackBot(Channel):
    """Slack bot channel — connects Slack to the assistant via Socket Mode."""

    name = "slack"

    @classmethod
    def is_configured(cls) -> bool:
        return bool(os.getenv("SLACK_BOT_TOKEN") and os.getenv("SLACK_APP_TOKEN"))

    def __init__(self, assistant):
        super().__init__(assistant)
        self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.app_token = os.getenv("SLACK_APP_TOKEN")
        self.allowed_users = [u.strip() for u in os.getenv("SLACK_USER_ID", "").split(",") if u.strip()]
        self.model_hint = os.getenv("SLACK_MODEL_HINT", "sonnet")
        self.app = None
        self.handler = None
        self._task = None

    async def start(self):
        self.app = AsyncApp(token=self.bot_token)
        self._register_handlers()

        self.handler = AsyncSocketModeHandler(self.app, self.app_token)
        self._task = asyncio.create_task(self.handler.start_async())

        logger.info(f"Slack bot started (Socket Mode) for {len(self.allowed_users)} users")

    async def stop(self):
        if self.handler:
            await self.handler.close_async()
        if self._task:
            self._task.cancel()
        logger.info("Slack bot stopped")

    def _authorized(self, user_id: str) -> bool:
        if not self.allowed_users:
            return True
        return user_id in self.allowed_users

    def _channel_name(self, slack_id: str) -> str:
        return f"slack_{slack_id}"

    def _register_handlers(self):
        @self.app.event("message")
        async def handle_message_event(event, say):
            if event.get("channel_type") != "im":
                return
            if event.get("bot_id") or event.get("subtype"):
                return

            slack_user_id = event.get("user")
            text = event.get("text", "")

            if not self._authorized(slack_user_id):
                await say("Unauthorized. Contact bot admin.")
                return

            # Keyword commands in DMs
            lower = text.strip().lower()
            if lower in ("help", "/help"):
                await say(self._help_text())
                return
            elif lower in ("status", "/status"):
                await say(self._status_text(slack_user_id))
                return
            elif lower in ("memory", "/memory"):
                await say(self._memory_text())
                return
            elif lower in ("forget", "/forget"):
                self.assistant.context_manager.clear_memory()
                await say("Memory cleared!")
                return

            # Handle file uploads
            files = event.get("files", [])
            if files:
                text = await self._handle_file(slack_user_id, files[0], text)

            await self._process_and_reply(slack_user_id, text, say)

        @self.app.event("app_mention")
        async def handle_mention(event, say):
            slack_user_id = event.get("user")
            text = event.get("text", "")

            if not self._authorized(slack_user_id):
                await say("Unauthorized. Contact bot admin.")
                return

            text = re.sub(r'<@[A-Za-z0-9]+>\s*', '', text).strip()
            if not text:
                await say("How can I help? Send me a message!")
                return

            await self._process_and_reply(slack_user_id, text, say, thread_ts=event.get("ts"))

    async def _process_and_reply(self, slack_user_id, text, say, thread_ts=None):
        channel = self._channel_name(slack_user_id)
        logger.info(f"Message from {channel}: {text[:50]}...")

        try:
            result = await self.assistant.process_message(
                channel=channel, message=text, model_hint=self.model_hint,
            )
            response = result.get("response", "Sorry, I couldn't process that.")
            if len(response) > 3000:
                for i in range(0, len(response), 3000):
                    await say(response[i:i + 3000], thread_ts=thread_ts)
            else:
                await say(response, thread_ts=thread_ts)
        except Exception as e:
            logger.error(f"Error processing Slack message: {e}")
            await say(f"Error: {str(e)}", thread_ts=thread_ts)

    async def _handle_file(self, slack_user_id, file_info, caption):
        channel = self._channel_name(slack_user_id)
        file_name = file_info.get("name", "uploaded_file")
        file_url = file_info.get("url_private_download")

        if not file_url:
            return caption or "File received but could not be downloaded"

        try:
            workspace = self.assistant.context_manager.workspace_dir
            files_dir = workspace / "files"
            files_dir.mkdir(exist_ok=True)

            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(file_url, headers={"Authorization": f"Bearer {self.bot_token}"})
                (files_dir / file_name).write_bytes(resp.content)

            logger.info(f"Downloaded file from {channel}: {file_name}")
            return f"File saved: {file_name}\n\n{caption or 'Please review this file'}"
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return caption or "File received but download failed"

    def _help_text(self):
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
            "- Upload files in our DM for analysis"
        )

    def _status_text(self, slack_user_id):
        channel = self._channel_name(slack_user_id)
        history = self.assistant.context_manager.get_history(channel, limit=100)
        return (
            f"*Bot Status:* Online\n\n"
            f"Channel: {channel}\n"
            f"Messages: {len(history)} in history"
        )

    def _memory_text(self):
        memory = self.assistant.context_manager.get_memory()
        if len(memory.strip()) <= 50:
            return "Memory is empty. I'll remember facts as we chat!"
        if len(memory) > 3000:
            memory = memory[:3000] + "\n\n... (truncated)"
        return f"*Memory:*\n\n{memory}"

    async def send_message(self, channel_or_user_id, message):
        """Send message to channel or user (for heartbeat notifications)."""
        if self.app:
            try:
                await self.app.client.chat_postMessage(channel=channel_or_user_id, text=message)
            except Exception as e:
                logger.error(f"Failed to send Slack message: {e}")
