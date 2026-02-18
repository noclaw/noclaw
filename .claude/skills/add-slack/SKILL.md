# Set Up Slack Bot

When the user runs `/add-slack`, walk them through setting up the Slack channel.

The Slack channel plugin is already built into NoClaw at `server/channels/slack_bot.py`. It auto-starts when the required env vars are set. This skill just helps the user set up those env vars.

## Step 1: Check dependency

Run:
```bash
pip install slack-bolt
```

## Step 2: Walk through Slack setup

**2a. Create the Slack App:**

Tell the user:
> To create your Slack bot:
> 1. Go to **https://api.slack.com/apps** and click **Create New App**
> 2. Choose **From scratch**
> 3. Give it a name (e.g. "NoClaw Assistant") and select your workspace
> 4. Click **Create App**

**2b. Enable Socket Mode:**

Tell the user:
> Enable Socket Mode (lets the bot connect without a public URL):
> 1. In the left sidebar, click **Socket Mode**
> 2. Toggle **Enable Socket Mode** to ON
> 3. Give the token a name like "noclaw-socket" and click **Generate**
> 4. Copy the **App-Level Token** (starts with `xapp-`)

Then ask: "What is your App-Level Token (starts with `xapp-`)?"

**2c. Set up Bot Token Scopes and Install:**

Tell the user:
> Set up permissions and install the bot:
> 1. Go to **OAuth & Permissions**
> 2. Under **Bot Token Scopes**, add:
>    - `app_mentions:read`, `chat:write`, `files:read`, `im:history`, `im:read`, `im:write`
> 3. Click **Install to Workspace**, then **Allow**
> 4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

Then ask: "What is your Bot User OAuth Token (starts with `xoxb-`)?"

**2d. Subscribe to Events:**

Tell the user:
> Enable event subscriptions:
> 1. Go to **Event Subscriptions** and toggle ON
> 2. Under **Subscribe to bot events**, add: `app_mention`, `message.im`
> 3. Click **Save Changes**
> 4. Go back to **OAuth & Permissions** and click **Reinstall to Workspace**

**2e. Enable Messages Tab:**

Tell the user:
> Enable DMs:
> 1. Go to **App Home**
> 2. Toggle **Messages Tab** ON
> 3. Check **Allow users to send Slash commands and messages from the messages tab**

**2f. Get Slack User ID:**

Tell the user:
> To get your Slack user ID:
> 1. Click your profile picture → **Profile** → three dots (**...**) → **Copy member ID**

Then ask: "What is your Slack member ID (starts with U)?"

**2g. Optional model hint:**

Ask the user which default model they want:
- **haiku** — fastest, cheapest
- **sonnet** — balanced (default)
- **opus** — most capable

## Step 3: Write to `.env`

Add or update these lines in the `.env` file:
```
SLACK_BOT_TOKEN=<their bot token>
SLACK_APP_TOKEN=<their app token>
SLACK_USER_ID=<their user ID>
SLACK_MODEL_HINT=<their choice, default: sonnet>
```

## Step 4: Verify

Run:
```bash
python -c "from server.channels.slack_bot import SlackBot; print('OK')"
```

Then tell the user:
> Slack is configured! Restart NoClaw to activate:
> ```
> python run_assistant.py
> ```
> Then send a DM to your bot in Slack to test it.

## Customization

If the user wants to customize the Slack bot beyond what env vars provide, they can edit `server/channels/slack_bot.py` directly. The channel plugin follows a standard interface — see `docs/PLUGINS.md` for details.
