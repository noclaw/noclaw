"""Telegram channel plugin for NoClaw."""

import os
import logging
import asyncio
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from .base import Channel

logger = logging.getLogger(__name__)


class TelegramBot(Channel):
    """Telegram bot channel — connects Telegram to the assistant."""

    name = "telegram"

    @classmethod
    def is_configured(cls) -> bool:
        return bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_USER_ID"))

    def __init__(self, assistant):
        super().__init__(assistant)
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.allowed_users = [int(uid.strip()) for uid in os.getenv("TELEGRAM_USER_ID", "").split(",") if uid.strip()]
        self.model_hint = os.getenv("TELEGRAM_MODEL_HINT", "sonnet")
        self.application = None

    async def start(self):
        self.application = Application.builder().token(self.bot_token).build()

        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))
        self.application.add_handler(CommandHandler("status", self._cmd_status))
        self.application.add_handler(CommandHandler("memory", self._cmd_memory))
        self.application.add_handler(CommandHandler("forget", self._cmd_forget))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        self.application.add_handler(MessageHandler(filters.VOICE, self._handle_voice))
        self.application.add_handler(MessageHandler(filters.Document.ALL, self._handle_document))
        self.application.add_handler(MessageHandler(filters.PHOTO, self._handle_photo))

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        logger.info(f"Telegram bot started for {len(self.allowed_users)} users")

    async def stop(self):
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        logger.info("Telegram bot stopped")

    def _authorized(self, user_id: int) -> bool:
        return user_id in self.allowed_users

    def _noclaw_user(self, telegram_id: int) -> str:
        return f"telegram_{telegram_id}"

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._authorized(update.effective_user.id):
            await update.message.reply_text("Unauthorized. Contact bot admin.")
            return
        await update.message.reply_text(
            "Welcome to your NoClaw AI Assistant!\n\n"
            "Commands: /help /status /memory /forget\n\n"
            "Just send me a message and I'll respond."
        )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._authorized(update.effective_user.id):
            await update.message.reply_text("Unauthorized.")
            return
        await update.message.reply_text(
            "NoClaw AI Assistant\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/help - Show this message\n"
            "/status - Check bot status\n"
            "/memory - View remembered facts\n"
            "/forget - Clear memory\n\n"
            "Send any text message to chat."
        )

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._authorized(update.effective_user.id):
            await update.message.reply_text("Unauthorized.")
            return
        user_id = self._noclaw_user(update.effective_user.id)
        user_context = self.assistant.context_manager.get_user_context(user_id)
        history = self.assistant.context_manager.get_history(user_id, limit=100)
        await update.message.reply_text(
            f"Bot Status: Online\n\n"
            f"Messages: {len(history)} in history\n"
            f"Workspace: {user_context['workspace_path']}\n"
            f"Last active: {user_context.get('last_active', 'Unknown')}"
        )

    async def _cmd_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._authorized(update.effective_user.id):
            await update.message.reply_text("Unauthorized.")
            return
        user_id = self._noclaw_user(update.effective_user.id)
        memory = self.assistant.context_manager.get_memory(user_id)
        if len(memory.strip()) <= 50:
            await update.message.reply_text("Memory is empty. I'll remember facts as we chat!")
        else:
            if len(memory) > 4000:
                memory = memory[:4000] + "\n\n... (truncated)"
            await update.message.reply_text(f"Memory:\n\n{memory}")

    async def _cmd_forget(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._authorized(update.effective_user.id):
            await update.message.reply_text("Unauthorized.")
            return
        user_id = self._noclaw_user(update.effective_user.id)
        self.assistant.context_manager.clear_memory(user_id)
        await update.message.reply_text("Memory cleared!")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._authorized(update.effective_user.id):
            await update.message.reply_text("Unauthorized.")
            return
        user_id = self._noclaw_user(update.effective_user.id)
        message = update.message.text
        logger.info(f"Message from {user_id}: {message[:50]}...")
        await update.message.chat.send_action("typing")

        try:
            result = await self.assistant.process_message(
                user=user_id, message=message, model_hint=self.model_hint,
            )
            response = result.get("response", "Sorry, I couldn't process that.")
            if len(response) > 4096:
                for i in range(0, len(response), 4000):
                    await update.message.reply_text(response[i:i + 4000])
            else:
                await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(f"Error: {str(e)}")

    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._authorized(update.effective_user.id):
            return
        await update.message.reply_text("Voice messages aren't supported yet. Please send text instead.")

    async def _handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._authorized(update.effective_user.id):
            return
        user_id = self._noclaw_user(update.effective_user.id)
        document = update.message.document
        logger.info(f"Document from {user_id}: {document.file_name}")

        try:
            user_context = self.assistant.context_manager.get_user_context(user_id)
            workspace = Path(user_context["workspace_path"])
            files_dir = workspace / "files"
            files_dir.mkdir(exist_ok=True)

            file_path = files_dir / document.file_name
            file = await document.get_file()
            await file.download_to_drive(file_path)

            caption = update.message.caption or "Please review this file"
            message = f"File saved: {document.file_name}\n\n{caption}"
            await update.message.chat.send_action("typing")

            result = await self.assistant.process_message(
                user=user_id, message=message, model_hint=self.model_hint,
            )
            await update.message.reply_text(result.get("response", "File received."))
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await update.message.reply_text(f"Error processing file: {str(e)}")

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._authorized(update.effective_user.id):
            return
        await update.message.reply_text("Photo received. Image analysis requires vision capabilities — I can only respond to your caption for now.")
        if update.message.caption:
            user_id = self._noclaw_user(update.effective_user.id)
            await update.message.chat.send_action("typing")
            result = await self.assistant.process_message(
                user=user_id, message=update.message.caption, model_hint=self.model_hint,
            )
            await update.message.reply_text(result.get("response", "Photo received."))

    async def send_message(self, telegram_user_id: int, message: str):
        """Send message to user (for heartbeat notifications)."""
        if self.application:
            try:
                await self.application.bot.send_message(chat_id=telegram_user_id, text=message)
            except Exception as e:
                logger.error(f"Failed to send Telegram message: {e}")
