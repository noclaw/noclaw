# Mac Mini Setup Guide

Set up NoClaw on a dedicated Mac Mini as an always-on personal AI assistant.

## Why a Dedicated Mac Mini?

NoClaw runs natively on macOS (not in Docker) because it needs:
- **Accessibility APIs** — mouse/keyboard control via cliclick
- **Screen Recording** — screenshots via screencapture
- **Native browser** — web browsing via agent-browser
- **AppleScript** — app scripting (TextEdit, Finder, Notes, AirDrop)

Security comes from the Mac Mini being a dedicated machine on the local network.

## Prerequisites

- macOS 13 (Ventura) or later
- Admin account for initial setup
- Local network access from your dev machine

## Step 1: Install Tools

### Required

```bash
# Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Node.js (for Claude Code CLI)
brew install node

# Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Python 3.10+
brew install python@3.12
```

### Optional (for Mac control skills)

```bash
# Mouse/keyboard automation
brew install cliclick

# Background processes (used by terminal-control skill)
brew install tmux

# uv (for workspace integration scripts — Gmail, Calendar, etc.)
brew install uv
```

## Step 2: Clone and Setup

```bash
git clone https://github.com/noclaw/noclaw.git
cd noclaw
python3 setup.py
```

The interactive setup handles:
- Prerequisite checks
- Platform detection (installs mac-control skill automatically)
- Python dependencies
- `.env` configuration
- Optional Telegram/Slack/Google setup

## Step 3: macOS Permissions

The agent needs these permissions to control the desktop. Grant them in **System Settings > Privacy & Security**.

### Accessibility (required for cliclick)

1. System Settings > Privacy & Security > Accessibility
2. Add **Terminal.app** (or your terminal emulator)
3. If running via launchd, also add the Python binary:
   ```bash
   which python3
   # e.g. /opt/homebrew/bin/python3.12
   ```

### Screen Recording (required for screencapture in agent context)

1. System Settings > Privacy & Security > Screen Recording
2. Add **Terminal.app**

### Full Disk Access (optional, for file operations outside workspace)

1. System Settings > Privacy & Security > Full Disk Access
2. Add **Terminal.app**

### Verify Permissions

```bash
# Test screenshot
screencapture -x /tmp/test_screen.png && echo "OK" && rm /tmp/test_screen.png

# Test cliclick
cliclick p  # Should print current mouse position
```

## Step 4: Network Configuration

### Enable SSH (Remote Login)

1. System Settings > General > Sharing > Remote Login > ON
2. Allow access for your user

```bash
# From your dev machine, test SSH
ssh youruser@mac-mini.local
```

### Firewall

1. System Settings > Network > Firewall > ON
2. Options > allow incoming connections for Python

Or use `pf` for finer control — allow port 3000 from local network only:

```bash
# /etc/pf.anchors/noclaw
pass in on en0 proto tcp from 192.168.0.0/16 to any port 3000
block in on en0 proto tcp from any to any port 3000
```

### Set a Static IP or Hostname

Give the Mac Mini a stable address:
- Router: assign a static DHCP lease
- Or set manually in System Settings > Network > Wi-Fi/Ethernet > Details > TCP/IP

The default mDNS hostname (`mac-mini.local`) works on local networks.

## Step 5: Energy Settings

System Settings > Energy:
- **Prevent automatic sleeping** — ON
- **Wake for network access** — ON
- **Start up automatically after a power failure** — ON (if available)

```bash
# Or via command line
sudo pmset -a sleep 0          # Never sleep
sudo pmset -a displaysleep 5   # Display sleeps after 5 min (saves energy)
sudo pmset -a womp 1           # Wake on LAN
sudo pmset -a autorestart 1    # Auto-restart after power failure
```

## Step 6: Auto-Start with launchd

Create a launch agent so NoClaw starts automatically on login.

```bash
# Create the plist
cat > ~/Library/LaunchAgents/com.noclaw.assistant.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.noclaw.assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/python3</string>
        <string>run_assistant.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/youruser/noclaw</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/youruser/noclaw/data/launchd-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/youruser/noclaw/data/launchd-stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
```

**Important:** Edit the plist to match your paths:
- Replace `/opt/homebrew/bin/python3` with the output of `which python3`
- Replace `/Users/youruser/noclaw` with your actual clone path

```bash
# Load the agent
launchctl load ~/Library/LaunchAgents/com.noclaw.assistant.plist

# Check status
launchctl list | grep noclaw

# View logs
tail -f ~/noclaw/data/launchd-stderr.log

# Stop/start
launchctl stop com.noclaw.assistant
launchctl start com.noclaw.assistant

# Unload (disable auto-start)
launchctl unload ~/Library/LaunchAgents/com.noclaw.assistant.plist
```

## Step 7: Configure the CLI Client

On your **dev machine** (laptop), set up the `noclaw` CLI to talk to the Mac Mini.

Copy the client:
```bash
# From the noclaw repo on the Mac Mini, or download directly
scp mac-mini.local:~/noclaw/noclaw ~/bin/noclaw
chmod +x ~/bin/noclaw
```

Configure it:
```bash
cat > ~/.noclaw << 'EOF'
url=http://mac-mini.local:3000
api_key=your-secret-key
EOF
```

Test it:
```bash
noclaw health
noclaw send "Hello from my laptop"
noclaw reply "Thanks"
```

## Step 8: Verify Everything

```bash
# On the Mac Mini
python run_assistant.py  # or check launchd status

# From your dev machine
noclaw health              # Server responding
noclaw send "Take a screenshot and describe what you see"
noclaw send "What's today's date?"
noclaw status              # Check active sessions
noclaw dashboard           # Open web dashboard
```

## Troubleshooting

### "Permission denied" for screencapture/cliclick
- Check System Settings > Privacy & Security
- The permissions must be granted to the process running the agent (Terminal.app or the Python binary for launchd)

### Server not reachable from dev machine
- Check firewall settings
- Verify the Mac Mini's IP: `ifconfig en0 | grep inet`
- Try `curl http://<mac-mini-ip>:3000/health` from the dev machine

### launchd not starting the server
- Check logs: `cat ~/noclaw/data/launchd-stderr.log`
- Verify Python path in the plist matches `which python3`
- Ensure `.env` file exists with `CLAUDE_CODE_OAUTH_TOKEN`
- Test manually first: `cd ~/noclaw && python3 run_assistant.py`

### Agent timeout
- Increase `AGENT_TIMEOUT` in `.env` (default: 300 seconds)
- Check Claude token: the agent needs a valid `CLAUDE_CODE_OAUTH_TOKEN`

### Wake on LAN not working
- Ensure the Mac Mini is connected via Ethernet (Wi-Fi WoL is unreliable)
- Verify: `pmset -g | grep womp` should show `1`
