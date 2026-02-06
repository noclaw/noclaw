# Add Slack Bot Skill

Adds Slack bot integration to NoClaw for workplace assistant access.

## What This Skill Does

Creates a Slack app that connects to your NoClaw assistant, bringing AI capabilities to your workspace.

**Use this skill for:**
- Workplace productivity
- Team collaboration
- Meeting notes and summaries
- Code review assistance
- Quick answers to work questions

## Installation

1. Create Slack app at https://api.slack.com/apps
2. Get bot token
3. Run `/add-slack`
4. Configure `.env`:
   ```bash
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_APP_TOKEN=xapp-your-token  # For Socket Mode
   ```
5. Restart NoClaw

## Features

- **Slash Commands** - `/ask`, `/help`, `/status`
- **Mentions** - @YourBot question here
- **DMs** - Private conversations
- **Threads** - Keep conversations organized
- **File Sharing** - Upload and analyze files
- **Reactions** - Quick feedback
- **Home Tab** - Personal dashboard

## Dependencies

- `slack-sdk` - Slack API library
- `slack-bolt` - Slack Bolt framework

## Configuration

```bash
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token  # For Socket Mode
SLACK_SIGNING_SECRET=your-secret
SLACK_WORKSPACE_ID=T1234567  # Optional
SLACK_MODEL_HINT=sonnet  # Default model
```

## Usage Examples

### Slash Commands
```
/ask What's our company policy on remote work?
/summarize #general from last week
/help
```

### Mentions
```
@YourBot draft an email to the team
@YourBot review this code snippet
```

### Threads
Reply in threads to maintain context without cluttering channels.

## Integration Features

- **Channel Integration** - Respond in public channels
- **Thread Support** - Maintain conversation context
- **File Uploads** - Analyze shared documents
- **Emoji Reactions** - Quick feedback
- **User Preferences** - Per-user settings
- **Team Management** - Role-based access

## Security

- OAuth-based authentication
- Workspace-scoped tokens
- Per-user data isolation
- Channel permissions respected
- Audit logs available

## Deployment Options

### Socket Mode (Easier)
- No public URL needed
- Good for development/testing
- Simpler setup

### HTTP Mode (Production)
- Webhook-based
- Requires public HTTPS URL
- Better for scale

## See Also

- [Slack API Documentation](https://api.slack.com/)
- [Slack Bolt Framework](https://slack.dev/bolt-python/)
- Full setup guide in `.claude/skills/add-slack/install.py`
