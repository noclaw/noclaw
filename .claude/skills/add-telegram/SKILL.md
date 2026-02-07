# Add Telegram Bot

When the user runs `/add-telegram`, perform ALL of the following steps to add Telegram bot support to NoClaw.

## Step 1: Install dependency

Run:
```bash
pip install python-telegram-bot
```

And add `python-telegram-bot>=21.0` to `server/requirements.txt` if not already present.

## Step 2: Create `server/channels/` directory

Create `server/channels/__init__.py` (empty file) if it doesn't exist.

## Step 3: Create `server/channels/telegram_bot.py`

Copy the reference implementation from `.claude/skills/add-telegram/telegram_bot.py` to `server/channels/telegram_bot.py`.

**Before copying, verify the reference implementation matches the current assistant.py interface:**
- `TelegramBot.__init__` takes `(assistant, bot_token, allowed_users)`
- `handle_message` calls `self.assistant.process_message(user=..., message=..., model_hint=...)`
- The `process_message` call signature must match `assistant.py`'s `process_message(self, user, message, workspace_path=None, extra_context=None, model_hint=None)`

## Step 4: Wire into `server/assistant.py`

Make these changes to `server/assistant.py`:

**Add import** (after other imports from `.`):
```python
from .channels.telegram_bot import TelegramBot
```

**Add to `PersonalAssistant.__init__`** (after `self.dashboard = ...`):
```python
# Telegram bot (if configured)
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
if bot_token:
    allowed_users = [u.strip() for u in os.getenv("TELEGRAM_USER_ID", "").split(",") if u.strip()]
    self.telegram_bot = TelegramBot(self, bot_token, allowed_users)
else:
    self.telegram_bot = None
```

**Add to `startup_event`** (after heartbeat start):
```python
if assistant.telegram_bot:
    await assistant.telegram_bot.start()
    logger.info("Telegram bot started")
```

**Add to `shutdown` method** (before existing shutdown logic):
```python
if self.telegram_bot:
    await self.telegram_bot.stop()
```

## Step 5: Add env vars to `.env.example`

Add these lines to `.env.example` (if not already present):
```bash
# Telegram Bot (optional - add via /add-telegram skill)
# TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
# TELEGRAM_USER_ID=your_numeric_telegram_id
# TELEGRAM_MODEL_HINT=sonnet
```

## Step 6: Create `docs/TELEGRAM.md`

Create a reference doc at `docs/TELEGRAM.md` covering:
- How the bot works (message flow: Telegram -> Bot -> NoClaw webhook -> Container -> Claude)
- User mapping (`telegram_{user_id}`)
- Available bot commands (/start, /help, /status, /memory, /forget)
- Supported message types (text, documents, photos)
- Environment variables (TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, TELEGRAM_MODEL_HINT)
- How to allow multiple users (comma-separated TELEGRAM_USER_ID)
- Troubleshooting (bot not responding, unauthorized errors)
- How to remove the integration

Keep it concise — this is a reference, not a tutorial. The interactive setup in Step 7 handles the tutorial part.

## Step 7: Walk the user through Telegram setup

After completing all code changes, guide the user interactively through setup. Ask questions and wait for answers at each step.

**7a. Create the bot:**

Tell the user:
> To create your Telegram bot:
> 1. Open Telegram and search for **@BotFather**
> 2. Send `/newbot`
> 3. Choose a name (e.g. "My Assistant") and username (e.g. "my_noclaw_bot")
> 4. BotFather will give you a token like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

Then ask: "What is your bot token from BotFather?"

**7b. Get user ID:**

Tell the user:
> To get your Telegram user ID:
> 1. Search for **@userinfobot** on Telegram
> 2. Send `/start`
> 3. It will reply with your numeric user ID

Then ask: "What is your Telegram user ID?"

**7c. Write to `.env`:**

Once you have both values, add them to the `.env` file:
```
TELEGRAM_BOT_TOKEN=<their token>
TELEGRAM_USER_ID=<their user ID>
```

If the `.env` file doesn't exist, create it from `.env.example`.

**7d. Optional model hint:**

Ask the user which default model they want for Telegram messages:
- **haiku** — fastest, cheapest (~$0.001/msg)
- **sonnet** — balanced (default, ~$0.003/msg)
- **opus** — most capable (~$0.015/msg)

Add `TELEGRAM_MODEL_HINT=<choice>` to `.env`.

**7e. Verify and tell user to restart:**

Verify the import works:
```bash
python -c "from server.channels.telegram_bot import TelegramBot; print('OK')"
```

Then tell the user:
> Telegram bot is configured! Restart NoClaw to activate:
> ```
> python run_assistant.py
> ```
> Then send `/start` to your bot on Telegram to test it.

## Important Notes

- Do NOT run install.py — make all changes directly
- Verify imports work before telling the user you're done
- If `server/channels/` already exists, don't overwrite existing files in it
- Never commit the `.env` file — it contains secrets
