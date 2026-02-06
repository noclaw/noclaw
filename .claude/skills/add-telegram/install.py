#!/usr/bin/env python3
"""
Install Telegram Bot Skill

Adds Telegram bot integration to NoClaw.
"""

import subprocess
import sys
from pathlib import Path
import shutil

def main():
    print("=" * 60)
    print("Installing Telegram Bot Skill")
    print("=" * 60)

    # Get project root
    project_root = Path(__file__).parent.parent.parent.parent
    server_dir = project_root / "server"
    channels_dir = server_dir / "channels"
    docs_dir = project_root / "docs"

    print(f"\nProject root: {project_root}")

    # Step 1: Install dependencies
    print("\n[1/4] Installing python-telegram-bot...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "python-telegram-bot"],
            check=True,
            capture_output=True
        )
        print("✅ python-telegram-bot installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install python-telegram-bot: {e}")
        return False

    # Step 2: Create channels directory
    print("\n[2/4] Creating channels directory...")
    channels_dir.mkdir(exist_ok=True)
    (channels_dir / "__init__.py").touch()
    print("✅ Created server/channels/")

    # Step 3: Copy bot implementation
    print("\n[3/4] Copying Telegram bot...")
    source_file = Path(__file__).parent / "telegram_bot.py"
    target_file = channels_dir / "telegram_bot.py"

    if source_file.exists():
        shutil.copy(source_file, target_file)
        print(f"✅ Copied to {target_file}")
    else:
        print(f"❌ Source file not found: {source_file}")
        return False

    # Step 4: Create documentation
    print("\n[4/4] Creating documentation...")
    doc_content = """# Telegram Bot Integration

Your NoClaw assistant is now accessible via Telegram!

## Setup

### 1. Get Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow prompts
3. Save your bot token

### 2. Get Your User ID

1. Search for `@userinfobot` on Telegram
2. Send `/start`
3. Note your numeric user ID

### 3. Configure Environment

Add to `.env`:

```bash
# Required
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_USER_ID=123456789

# Optional
TELEGRAM_ALLOWED_USERS=123,456,789  # Multiple users (comma-separated)
TELEGRAM_MODEL_HINT=sonnet  # Default model (haiku/sonnet/opus)
```

### 4. Update assistant.py

Add to `server/assistant.py`:

```python
# After imports
from .channels.telegram_bot import TelegramBot

# In PersonalAssistant.__init__()
# Initialize Telegram bot if configured
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
if bot_token:
    allowed_users = os.getenv("TELEGRAM_USER_ID", "").split(",")
    self.telegram_bot = TelegramBot(self, bot_token, allowed_users)
else:
    self.telegram_bot = None

# In startup_event()
if assistant.telegram_bot:
    await assistant.telegram_bot.start()
    logger.info("Telegram bot started")

# In shutdown()
if self.telegram_bot:
    await self.telegram_bot.stop()
```

### 5. Restart NoClaw

```bash
python run_assistant.py
```

## Usage

### Commands

- `/start` - Start the bot
- `/help` - Show help
- `/status` - Check status
- `/memory` - View remembered facts
- `/forget` - Clear memory

### Messaging

Just send messages to your bot:
- Text messages
- Voice messages (transcribed)
- Documents (analyzed)
- Photos (described)

### Multiple Users

Allow multiple Telegram users:

```bash
TELEGRAM_ALLOWED_USERS=123456789,987654321,555555555
```

Each user gets isolated:
- Workspace: `data/workspaces/telegram_{user_id}/`
- Memory: Separate for each user
- Context: Independent

## Heartbeat Notifications

To enable heartbeat notifications via Telegram:

1. Enable heartbeat for user:
   ```bash
   curl -X POST http://localhost:3000/heartbeat/telegram_123456789/enable
   ```

2. Update `server/heartbeat.py` to send Telegram notifications:
   ```python
   # In _run_heartbeat_for_user()
   if "HEARTBEAT_OK" not in response:
       # Send to Telegram if user has telegram ID
       if user_id.startswith("telegram_"):
           telegram_id = int(user_id.replace("telegram_", ""))
           if self.assistant.telegram_bot:
               await self.assistant.telegram_bot.send_message(
                   telegram_id,
                   f"⏰ Heartbeat Alert:\\n\\n{response}"
               )
   ```

## Troubleshooting

### Bot Not Responding

1. Check token:
   ```bash
   echo $TELEGRAM_BOT_TOKEN
   ```

2. Check logs:
   ```bash
   tail -f data/noclaw.log | grep telegram
   ```

3. Test bot manually:
   ```bash
   python server/channels/telegram_bot.py
   ```

### "Unauthorized" Message

- Verify user ID in `.env`
- Check ID is numeric (not username)
- Restart server after changing `.env`

## Security

- Bot token is secret - never commit to git
- Add to `.gitignore`:
  ```
  .env
  ```
- Only authorized users can chat
- Each user has isolated workspace

## See Also

- [python-telegram-bot docs](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
"""

    doc_file = docs_dir / "TELEGRAM.md"
    doc_file.write_text(doc_content)
    print(f"✅ Created {doc_file}")

    # Success summary
    print("\n" + "=" * 60)
    print("✅ Telegram Bot Skill Installed Successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Get bot token from @BotFather on Telegram")
    print("2. Get your user ID from @userinfobot")
    print("3. Add to .env:")
    print("   TELEGRAM_BOT_TOKEN=your_token_here")
    print("   TELEGRAM_USER_ID=your_id_here")
    print("4. Update server/assistant.py (see docs/TELEGRAM.md)")
    print("5. Restart NoClaw: python run_assistant.py")
    print("\nSee docs/TELEGRAM.md for complete setup instructions")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
