# Set Up Telegram Bot

When the user runs `/add-telegram`, walk them through setting up the Telegram channel.

The Telegram channel plugin is already built into NoClaw at `server/channels/telegram_bot.py`. It auto-starts when the required env vars are set. This skill just helps the user set up those env vars.

## Step 1: Check dependency

Run:
```bash
pip install python-telegram-bot
```

## Step 2: Walk through Telegram setup

**2a. Create the bot:**

Tell the user:
> To create your Telegram bot:
> 1. Open Telegram and search for **@BotFather**
> 2. Send `/newbot`
> 3. Choose a name (e.g. "My Assistant") and username (e.g. "my_noclaw_bot")
> 4. BotFather will give you a token like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

Then ask: "What is your bot token from BotFather?"

**2b. Get user ID:**

Tell the user:
> To get your Telegram user ID:
> 1. Search for **@userinfobot** on Telegram
> 2. Send `/start`
> 3. It will reply with your numeric user ID

Then ask: "What is your Telegram user ID?"

**2c. Optional model hint:**

Ask the user which default model they want for Telegram messages:
- **haiku** — fastest, cheapest
- **sonnet** — balanced (default)
- **opus** — most capable

## Step 3: Write to `.env`

Add or update these lines in the `.env` file:
```
TELEGRAM_BOT_TOKEN=<their token>
TELEGRAM_USER_ID=<their user ID>
TELEGRAM_MODEL_HINT=<their choice, default: sonnet>
```

## Step 4: Verify

Run:
```bash
python -c "from server.channels.telegram_bot import TelegramBot; print('OK')"
```

Then tell the user:
> Telegram is configured! Restart NoClaw to activate:
> ```
> python run_assistant.py
> ```
> Then send `/start` to your bot on Telegram to test it.

## Customization

If the user wants to customize the Telegram bot beyond what env vars provide, they can edit `server/channels/telegram_bot.py` directly. The channel plugin follows a standard interface — see `docs/PLUGINS.md` for details.
