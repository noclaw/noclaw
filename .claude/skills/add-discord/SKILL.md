# Add Discord Bot Skill

Adds Discord bot integration to NoClaw for server-based AI assistant access.

## What This Skill Does

Creates a Discord bot that connects to your NoClaw assistant, allowing you to chat with Claude in Discord servers and DMs.

**Use this skill for:**
- Team chat integration
- Discord server assistant
- Voice channel transcription
- Server moderation help
- Gaming community assistant

## Installation

1. Create Discord bot at https://discord.com/developers/applications
2. Get bot token
3. Run `/add-discord`
4. Configure `.env`:
   ```bash
   DISCORD_BOT_TOKEN=your_token_here
   DISCORD_GUILD_ID=your_server_id  # Optional, for guild commands
   ```
5. Restart NoClaw

## Features

- **Slash Commands** - `/ask`, `/help`, `/status`, `/memory`
- **Mentions** - @YourBot question here
- **DM Support** - Private conversations
- **Thread Support** - Keep conversations organized
- **File Uploads** - Share and analyze files
- **Voice Transcription** - Process voice messages (if enabled)

## Dependencies

- `discord.py` - Discord API library

## Configuration

```bash
DISCORD_BOT_TOKEN=your_token_here
DISCORD_PREFIX=!  # Command prefix (default: /)
DISCORD_GUILD_ID=123456789  # Optional: restrict to server
DISCORD_ADMIN_ROLES=Admin,Moderator  # Comma-separated role names
DISCORD_MODEL_HINT=sonnet  # Default model
```

## Usage Examples

### Slash Commands
```
/ask What's the weather like?
/status
/memory show
/help
```

### Mentions
```
@YourBot explain quantum computing
@YourBot help me with Python
```

### Threads
Create threads for long conversations to keep channels clean.

## Security

- Bot permissions: Read Messages, Send Messages, Use Slash Commands
- Role-based access control
- Per-user isolated contexts
- Server-specific or global deployment

## See Also

- [discord.py documentation](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers)
- Full setup guide in `.claude/skills/add-discord/install.py`
