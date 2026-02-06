# Add Telegram Bot Skill

Adds Telegram bot integration to NoClaw for chat-based AI assistant access.

## What This Skill Does

This skill adds a Telegram bot that connects to your NoClaw assistant, allowing you to chat with Claude via Telegram.

**Use this skill when you want:**
- Chat with your AI assistant via Telegram
- Mobile access to your assistant
- Quick voice messages to your assistant
- Share files and images with Claude
- Get notifications from heartbeat checks

## What This Skill Adds

### Files Added
- `server/channels/telegram_bot.py` - Telegram bot implementation
- `docs/TELEGRAM.md` - Setup and usage documentation

### Dependencies Added
- `python-telegram-bot` - Telegram Bot API library

### API Changes
- No new endpoints (uses webhook internally)
- Bot runs as background service

### Configuration Required
- Telegram bot token from @BotFather
- Your Telegram user ID
- Webhook URL (optional, for production)

## Installation

### Step 1: Create Telegram Bot

1. **Talk to BotFather:**
   - Open Telegram and search for `@BotFather`
   - Send `/newbot`
   - Follow prompts to create your bot
   - Save the bot token (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

2. **Get Your User ID:**
   - Search for `@userinfobot` on Telegram
   - Send `/start`
   - Note your user ID (numeric)

### Step 2: Install Skill

Run the skill:
```bash
/add-telegram
```

Or manually:
```bash
python .claude/skills/add-telegram/install.py
```

### Step 3: Configure

Add to `.env`:
```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_USER_ID=123456789
```

### Step 4: Start Bot

Restart NoClaw:
```bash
python run_assistant.py
```

The bot will start automatically and send you a "Bot started!" message.

## Usage

### Basic Chat

Just send messages to your bot:
```
You: What's the weather like today?
Bot: I'll check the weather for you...
```

### Voice Messages

Send voice messages (Telegram will transcribe):
```
🎤 Voice message → Text → Claude
```

### File Sharing

Send files to share with Claude:
```
You: [sends file.py]
You: Review this code

Bot: I'll review your Python file...
```

### Photos

Send photos for analysis:
```
You: [sends photo]
You: What's in this image?

Bot: I see...
```

### Commands

Built-in bot commands:
- `/start` - Start the bot
- `/help` - Show help message
- `/status` - Check bot status
- `/memory` - View remembered facts
- `/forget` - Clear memory

## How It Works

### Message Flow

```
Telegram → Bot → NoClaw Webhook → Container → Claude SDK
                                              ↓
Telegram ← Bot ← Response ← Worker ← Container
```

### User Mapping

Each Telegram user ID maps to a NoClaw user:
- `telegram_{user_id}` (e.g., `telegram_123456789`)
- Separate workspace and memory per user
- Isolated contexts

### Security

- Bot only responds to authorized user IDs
- List configured in `TELEGRAM_USER_ID` (comma-separated for multiple)
- Unknown users get "Unauthorized" message

### Heartbeat Integration

When heartbeat detects something important:
```python
# In heartbeat result handler
if user has telegram:
    send_telegram_message(user, heartbeat_result)
```

## Configuration Options

### Environment Variables

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_USER_ID=your_user_id

# Optional
TELEGRAM_ALLOWED_USERS=123,456,789  # Multiple users
TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram  # For production
TELEGRAM_MODEL_HINT=sonnet  # Default model (haiku/sonnet/opus)
```

### Multiple Users

Allow multiple Telegram users:
```bash
TELEGRAM_ALLOWED_USERS=123456789,987654321,555555555
```

Each user gets their own:
- Workspace: `data/workspaces/telegram_123456789/`
- Memory: `data/workspaces/telegram_123456789/memory.md`
- Context: Isolated from other users

## Advanced Features

### Custom Commands

Edit `server/channels/telegram_bot.py`:

```python
@bot.command("remind")
async def remind_command(update, context):
    """Custom reminder command"""
    await update.message.reply_text("Reminder set!")
```

### Heartbeat Notifications

Enable in heartbeat.py:
```python
# If heartbeat finds something important
if result != "HEARTBEAT_OK":
    telegram_bot.send_message(user_id, result)
```

### File Processing

Bot automatically:
- Accepts documents (.pdf, .txt, .py, etc.)
- Downloads to workspace
- Includes file path in prompt
- Claude can read and process files

### Voice Message Transcription

Telegram automatically transcribes voice messages:
- Send voice message
- Telegram converts to text
- Text sent to Claude
- Response sent back

## Deployment

### Local Development

Run locally with polling:
```python
# In telegram_bot.py
application.run_polling()
```

### Production (Webhook)

Use webhook for better reliability:

1. **Set webhook URL:**
   ```bash
   TELEGRAM_WEBHOOK_URL=https://yourdomain.com/telegram
   ```

2. **Configure HTTPS:**
   - Telegram requires HTTPS
   - Use nginx/caddy as reverse proxy
   - Get SSL cert (Let's Encrypt)

3. **Update bot:**
   ```python
   # In telegram_bot.py
   application.run_webhook(
       listen="0.0.0.0",
       port=8443,
       webhook_url=TELEGRAM_WEBHOOK_URL
   )
   ```

## Troubleshooting

### Bot Not Responding

1. Check token is correct:
   ```bash
   echo $TELEGRAM_BOT_TOKEN
   ```

2. Check bot is running:
   ```bash
   curl http://localhost:3000/health
   ```

3. Check logs:
   ```bash
   tail -f data/noclaw.log | grep telegram
   ```

### "Unauthorized" Message

- Verify your user ID is in `TELEGRAM_USER_ID`
- Check spelling/formatting in .env
- Restart server after changing .env

### Messages Not Reaching Claude

- Check NoClaw is running
- Check container is working
- Test webhook directly:
  ```bash
  curl -X POST http://localhost:3000/webhook \
    -H "Content-Type: application/json" \
    -d '{"user": "telegram_123", "message": "test"}'
  ```

## Cost Optimization

Telegram messages use the same model hints as API:

**Default (Sonnet):** ~$0.003 per message
**Haiku:** ~$0.001 per message (set `TELEGRAM_MODEL_HINT=haiku`)
**Opus:** ~$0.015 per message (for complex tasks)

To minimize costs:
1. Set `TELEGRAM_MODEL_HINT=haiku` for most messages
2. Use explicit model switching in messages:
   - "Hey @haiku, quick question..."
   - "Hey @opus, analyze this in depth..."

## Privacy & Security

- Bot token is secret - never commit to git
- Only authorized users can chat
- Each user has isolated workspace
- Messages stored in local database only
- No data sent to Telegram except responses

## Examples

### Daily Briefing

```
You: Morning briefing please

Bot: Good morning! Here's your briefing:
- 3 unread emails
- Meeting at 10am: Sprint Planning
- No urgent notifications
Have a great day!
```

### Quick Calculation

```
You: What's 15% tip on $142.50?

Bot: 15% tip on $142.50 is $21.38
Total with tip: $163.88
```

### Code Review

```
You: [sends Python file]
You: Any issues with this code?

Bot: I reviewed your code. Here are some suggestions:
1. Line 23: Consider using pathlib instead of os.path
2. Line 45: This could raise KeyError, add try/except
3. Line 67: Function is doing too much, consider splitting

Overall structure looks good!
```

## Removal

To remove Telegram integration:

1. **Stop the bot:**
   - Remove from startup in assistant.py
   - Or comment out bot initialization

2. **Remove dependencies:**
   ```bash
   pip uninstall python-telegram-bot
   ```

3. **Clean .env:**
   - Remove TELEGRAM_* variables

4. **Revoke bot token:**
   - Talk to @BotFather
   - `/revoke` to disable bot

## See Also

- [python-telegram-bot documentation](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [BotFather commands](https://core.telegram.org/bots/features#botfather)
