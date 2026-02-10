# Add Slack Bot

When the user runs `/add-slack`, perform ALL of the following steps to add Slack bot support to NoClaw.

## Step 1: Install dependency

Run:
```bash
pip install slack-bolt
```

And add `slack-bolt>=1.18.0` to `server/requirements.txt` if not already present.

## Step 2: Create `server/channels/` directory

Create `server/channels/__init__.py` (empty file) if it doesn't exist.

## Step 3: Create `server/channels/slack_bot.py`

Copy the reference implementation from `.claude/skills/add-slack/slack_bot.py` to `server/channels/slack_bot.py`.

**Before copying, verify the reference implementation matches the current assistant.py interface:**
- `SlackBot.__init__` takes `(assistant, bot_token, app_token, allowed_users)`
- `_process_and_reply` calls `await self.assistant.process_message(user=..., message=..., model_hint=...)`
- The `process_message` call signature must match `assistant.py`'s `process_message(self, user, message, workspace_path=None, extra_context=None, model_hint=None)`

## Step 4: Wire into `server/assistant.py`

Make these changes to `server/assistant.py`:

**Add import** (after other channel imports):
```python
from .channels.slack_bot import SlackBot
```

**Add to `PersonalAssistant.__init__`** (after other bot initialization):
```python
# Slack bot (if configured)
slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
slack_app_token = os.getenv("SLACK_APP_TOKEN")
if slack_bot_token and slack_app_token:
    slack_allowed_users = [u.strip() for u in os.getenv("SLACK_USER_ID", "").split(",") if u.strip()]
    self.slack_bot = SlackBot(self, slack_bot_token, slack_app_token, slack_allowed_users)
else:
    self.slack_bot = None
```

**Add to `startup_event`** (after other bot starts):
```python
if assistant.slack_bot:
    await assistant.slack_bot.start()
    logger.info("Slack bot started")
```

**Add to `shutdown` method** (before existing shutdown logic):
```python
if self.slack_bot:
    await self.slack_bot.stop()
```

## Step 5: Add env vars to `.env.example`

Add these lines to `.env.example` (if not already present):
```bash
# Slack Bot (optional - add via /add-slack skill)
# SLACK_BOT_TOKEN=xoxb-your-bot-token
# SLACK_APP_TOKEN=xapp-your-app-level-token
# SLACK_USER_ID=U12345678
# SLACK_MODEL_HINT=sonnet
```

## Step 6: Create `docs/SLACK.md`

Create a reference doc at `docs/SLACK.md` covering:
- How the bot works (message flow: Slack -> Socket Mode -> NoClaw process_message() -> Container -> Claude -> Slack)
- User mapping (`slack_{user_id}`)
- Available commands (help, status, memory, forget — typed as keywords in DM or after @mention)
- Supported message types (text, file uploads, @mentions)
- Environment variables (SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_USER_ID, SLACK_MODEL_HINT)
- How to allow multiple users (comma-separated SLACK_USER_ID)
- Troubleshooting (bot not responding, unauthorized errors, @mentions not working)
- How to remove the integration

Keep it concise — this is a reference, not a tutorial. The interactive setup in Step 7 handles the tutorial part.

## Step 7: Walk the user through Slack setup

After completing all code changes, guide the user interactively through setup. Ask questions and wait for answers at each step.

**7a. Create the Slack App:**

Tell the user:
> To create your Slack bot:
> 1. Go to **https://api.slack.com/apps** and click **Create New App**
> 2. Choose **From scratch**
> 3. Give it a name (e.g. "NoClaw Assistant") and select your workspace
> 4. Click **Create App**

**7b. Enable Socket Mode:**

Tell the user:
> Enable Socket Mode (this lets the bot connect without a public URL):
> 1. In the left sidebar, click **Socket Mode**
> 2. Toggle **Enable Socket Mode** to ON
> 3. When prompted, give the token a name like "noclaw-socket" and click **Generate**
> 4. Copy the **App-Level Token** (starts with `xapp-`)

Then ask: "What is your App-Level Token (starts with `xapp-`)?"

**7c. Set up Bot Token Scopes and Install:**

Tell the user:
> Now set up permissions and install the bot:
> 1. In the left sidebar, go to **OAuth & Permissions**
> 2. Under **Bot Token Scopes**, add these scopes:
>    - `app_mentions:read` (receive @mentions)
>    - `chat:write` (send messages)
>    - `files:read` (read uploaded files)
>    - `im:history` (read DM messages)
>    - `im:read` (view DM info)
>    - `im:write` (open DMs)
> 3. Scroll up and click **Install to Workspace**, then **Allow**
> 4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

Then ask: "What is your Bot User OAuth Token (starts with `xoxb-`)?"

**7d. Subscribe to Events:**

Tell the user:
> Enable event subscriptions:
> 1. In the left sidebar, go to **Event Subscriptions**
> 2. Toggle **Enable Events** to ON
> 3. Under **Subscribe to bot events**, add:
>    - `app_mention` (when someone @mentions the bot)
>    - `message.im` (direct messages to the bot)
> 4. Click **Save Changes**
> 5. **Important:** Go back to **OAuth & Permissions** and click **Reinstall to Workspace** — event subscriptions added after the initial install don't take effect until you reinstall.
> (Socket Mode handles the connection automatically — no Request URL needed)

**7e. Enable Messages Tab:**

Tell the user:
> Enable the Messages tab so users can DM the bot:
> 1. In the left sidebar, go to **App Home**
> 2. Make sure **Messages Tab** is toggled ON
> 3. Check the box **Allow users to send Slash commands and messages from the messages tab**

**7f. Get your Slack User ID:**

Tell the user:
> To get your Slack user ID:
> 1. In Slack, click on your profile picture in the top right
> 2. Click **Profile**
> 3. Click the three dots (**...**) menu
> 4. Click **Copy member ID**

Then ask: "What is your Slack member ID (starts with U)?"

**7g. Write to `.env`:**

Once you have all three values, add them to the `.env` file:
```
SLACK_BOT_TOKEN=<their bot token>
SLACK_APP_TOKEN=<their app token>
SLACK_USER_ID=<their user ID>
```

If the `.env` file doesn't exist, create it from `.env.example`.

**7h. Optional model hint:**

Ask the user which default model they want for Slack messages:
- **haiku** — fastest, cheapest (~$0.001/msg)
- **sonnet** — balanced (default, ~$0.003/msg)
- **opus** — most capable (~$0.015/msg)

Add `SLACK_MODEL_HINT=<choice>` to `.env`.

**7i. Verify and tell user to restart:**

Verify the import works:
```bash
python -c "from server.channels.slack_bot import SlackBot; print('OK')"
```

Then tell the user:
> Slack bot is configured! Restart NoClaw to activate:
> ```
> python run_assistant.py
> ```
> Then send a DM to your bot in Slack or @mention it in a channel to test.

## Important Notes

- Do NOT run install.py — make all changes directly
- Verify imports work before telling the user you're done
- If `server/channels/` already exists, don't overwrite existing files in it
- Never commit the `.env` file — it contains secrets
