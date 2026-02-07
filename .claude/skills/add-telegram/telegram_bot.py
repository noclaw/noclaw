#!/usr/bin/env python3
"""
Telegram Bot for NoClaw

Provides Telegram chat interface to your personal AI assistant.
"""

import os
import logging
import asyncio
from typing import Optional
from pathlib import Path
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot that connects to NoClaw assistant"""

    def __init__(self, assistant, bot_token: str, allowed_users: list):
        """
        Initialize Telegram bot

        Args:
            assistant: Reference to PersonalAssistant
            bot_token: Telegram bot token from BotFather
            allowed_users: List of allowed Telegram user IDs
        """
        self.assistant = assistant
        self.bot_token = bot_token
        self.allowed_users = [int(uid) for uid in allowed_users]
        self.application = None

        logger.info(f"Telegram bot initialized for {len(allowed_users)} users")

    async def start(self):
        """Start the Telegram bot"""
        # Build application
        self.application = Application.builder().token(self.bot_token).build()

        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("memory", self.memory_command))
        self.application.add_handler(CommandHandler("forget", self.forget_command))

        # Message handlers
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message
        ))
        self.application.add_handler(MessageHandler(
            filters.VOICE,
            self.handle_voice
        ))
        self.application.add_handler(MessageHandler(
            filters.Document.ALL,
            self.handle_document
        ))
        self.application.add_handler(MessageHandler(
            filters.PHOTO,
            self.handle_photo
        ))

        # Start polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        logger.info("Telegram bot started")

    async def stop(self):
        """Stop the Telegram bot"""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        logger.info("Telegram bot stopped")

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        return user_id in self.allowed_users

    def get_user_id(self, telegram_id: int) -> str:
        """Map Telegram ID to NoClaw user ID"""
        return f"telegram_{telegram_id}"

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id

        if not self.is_authorized(user_id):
            await update.message.reply_text("⛔ Unauthorized. Contact bot admin.")
            logger.warning(f"Unauthorized access attempt from {user_id}")
            return

        welcome_message = """
👋 Welcome to your NoClaw AI Assistant!

I'm here to help you with tasks, answer questions, and keep you organized.

**Commands:**
/help - Show this help message
/status - Check my status
/memory - View what I remember about you
/forget - Clear my memory

**Usage:**
Just send me a message and I'll respond!
- Text messages
- Voice messages (I'll transcribe)
- Documents (I can read them)
- Photos (I can describe them)

Let's get started! What can I help you with?
"""
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ Unauthorized")
            return

        help_text = """
**NoClaw AI Assistant Help**

**Commands:**
/start - Start the bot
/help - Show this message
/status - Check bot status
/memory - View remembered facts
/forget - Clear memory

**Message Types:**
📝 Text - Send any message
🎤 Voice - I'll transcribe and respond
📎 Files - I can read and analyze
🖼️ Photos - I can describe images

**Tips:**
- Be specific in your requests
- I remember our conversation
- I can help with tasks, coding, questions, etc.

**Need more help?**
Check docs/TELEGRAM.md for detailed documentation.
"""
        await update.message.reply_text(help_text)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ Unauthorized")
            return

        user_id = self.get_user_id(update.effective_user.id)

        # Get user context
        user_context = self.assistant.context_manager.get_user_context(user_id)

        # Get recent message count
        history = self.assistant.context_manager.get_history(user_id, limit=100)

        status_text = f"""
**Bot Status**

✅ Online and ready

**Your Stats:**
- Messages: {len(history)} in history
- Workspace: {user_context['workspace_path']}
- Last active: {user_context.get('last_active', 'Unknown')}

**System:**
- Model: Auto-select (Haiku/Sonnet/Opus)
- Container: Isolated execution
- Memory: Persistent
"""
        await update.message.reply_text(status_text)

    async def memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /memory command"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ Unauthorized")
            return

        user_id = self.get_user_id(update.effective_user.id)
        memory = self.assistant.context_manager.get_memory(user_id)

        if len(memory.strip()) <= 50:  # Just header
            await update.message.reply_text("📝 Memory is empty. I'll remember facts as we chat!")
        else:
            # Truncate if too long for Telegram
            if len(memory) > 4000:
                memory = memory[:4000] + "\n\n... (truncated)"

            await update.message.reply_text(f"📝 **Memory:**\n\n{memory}")

    async def forget_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /forget command"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ Unauthorized")
            return

        user_id = self.get_user_id(update.effective_user.id)
        self.assistant.context_manager.clear_memory(user_id)

        await update.message.reply_text("🗑️ Memory cleared!")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ Unauthorized")
            return

        user_id = self.get_user_id(update.effective_user.id)
        message = update.message.text

        logger.info(f"Message from {user_id}: {message[:50]}...")

        # Send typing indicator
        await update.message.chat.send_action("typing")

        try:
            # Process with assistant
            result = await self.assistant.process_message(
                user=user_id,
                message=message,
                model_hint=os.getenv("TELEGRAM_MODEL_HINT", "sonnet")
            )

            response = result.get("response", "Sorry, I couldn't process that.")

            # Split long messages
            if len(response) > 4096:
                # Telegram has 4096 char limit
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ Unauthorized")
            return

        await update.message.reply_text("🎤 Voice messages aren't supported yet. Please send text instead.")

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ Unauthorized")
            return

        user_id = self.get_user_id(update.effective_user.id)
        document = update.message.document

        logger.info(f"Document from {user_id}: {document.file_name}")

        await update.message.reply_text(f"📎 Received {document.file_name}")

        # Download to workspace
        try:
            user_context = self.assistant.context_manager.get_user_context(user_id)
            workspace = Path(user_context["workspace_path"])
            files_dir = workspace / "files"
            files_dir.mkdir(exist_ok=True)

            file_path = files_dir / document.file_name
            file = await document.get_file()
            await file.download_to_drive(file_path)

            # Send follow-up message with file info
            caption = update.message.caption or "Please review this file"
            message = f"File saved: {document.file_name}\n\n{caption}"

            await update.message.chat.send_action("typing")

            result = await self.assistant.process_message(
                user=user_id,
                message=message,
                model_hint=os.getenv("TELEGRAM_MODEL_HINT", "sonnet")
            )

            await update.message.reply_text(result.get("response", "File received."))

        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await update.message.reply_text(f"❌ Error processing file: {str(e)}")

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo uploads"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ Unauthorized")
            return

        user_id = self.get_user_id(update.effective_user.id)

        await update.message.reply_text("🖼️ Photo received. Note: Image analysis requires Claude to have vision capabilities. I can only respond to your caption for now.")

        # If there's a caption, process it
        if update.message.caption:
            await update.message.chat.send_action("typing")

            result = await self.assistant.process_message(
                user=user_id,
                message=update.message.caption,
                model_hint=os.getenv("TELEGRAM_MODEL_HINT", "sonnet")
            )

            await update.message.reply_text(result.get("response", "Photo received."))

    async def send_message(self, telegram_user_id: int, message: str):
        """Send message to user (for heartbeat notifications)"""
        if self.application:
            try:
                await self.application.bot.send_message(
                    chat_id=telegram_user_id,
                    text=message
                )
                logger.info(f"Sent notification to {telegram_user_id}")
            except Exception as e:
                logger.error(f"Failed to send message: {e}")


async def main():
    """Test the bot locally"""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    users = os.getenv("TELEGRAM_USER_ID", "").split(",")

    if not token or not users[0]:
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_USER_ID must be set")
        sys.exit(1)

    # Create mock assistant for testing
    class MockAssistant:
        async def process_message(self, user, message, model_hint=None):
            return {"response": f"Echo: {message}"}

    bot = TelegramBot(MockAssistant(), token, users)
    await bot.start()

    print(f"Bot started! Send /start to your bot to test.")
    print(f"Press Ctrl+C to stop")

    try:
        # Keep running
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
