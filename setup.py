#!/usr/bin/env python3
"""
NoClaw Setup — Interactive setup script.

Consolidates all setup steps into one place:
  - Prerequisites check
  - agentpool installation
  - Python dependency installation
  - .env configuration (from .env.example template)
  - Telegram channel setup (optional)
  - Slack channel setup (optional)
  - Google integrations setup (optional, OAuth flow)

Stdlib only — no pip dependencies needed to run this script.
Safe to re-run (idempotent, backs up existing .env).
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NOCLAW_ROOT = Path(__file__).parent.resolve()
ENV_FILE = NOCLAW_ROOT / ".env"
ENV_EXAMPLE = NOCLAW_ROOT / ".env.example"
REQUIREMENTS = NOCLAW_ROOT / "server" / "requirements.txt"
MIN_PYTHON = (3, 10)
AGENTPOOL_REPO_URL = "https://github.com/noclaw/agentpool.git"
AGENTPOOL_DEFAULT_PATH = NOCLAW_ROOT.parent / "agentpool"

TOTAL_STEPS = 9

GOOGLE_CREDENTIALS_FILE = NOCLAW_ROOT / "google_credentials.json"
GOOGLE_TOKEN_FILE = NOCLAW_ROOT / "google_token.json"
# Old location (for auto-migration)
OLD_GOOGLE_CREDENTIALS = NOCLAW_ROOT / "workspace" / ".claude" / "scripts" / "integrations" / "google_credentials.json"
OLD_GOOGLE_TOKEN = NOCLAW_ROOT / "workspace" / ".claude" / "scripts" / "integrations" / "google_token.json"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Placeholder values in .env.example that should be treated as unset
PLACEHOLDERS = {
    "sk-ant-oat01-your-token-here",
    "sk-ant-your-api-key-here",
    "your-secret-key-here",
    "your-bot-token-from-botfather",
    "your-numeric-telegram-id",
    "xoxb-your-bot-token",
    "xapp-your-app-level-token",
    "U12345678",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_header(title: str) -> None:
    print()
    print("=" * 50)
    print(f"  {title}")
    print("=" * 50)
    print()


def print_step(num: int, title: str) -> None:
    print()
    print(f"--- Step {num}/{TOTAL_STEPS}: {title} ---")
    print()


def print_ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def print_warn(msg: str) -> None:
    print(f"  [!!] {msg}")


def print_skip(msg: str) -> None:
    print(f"  [--] {msg}")


def print_info(msg: str) -> None:
    print(f"  {msg}")


def prompt(message: str, default: str = "") -> str:
    """Prompt for input with optional default."""
    if default:
        raw = input(f"  {message} [{default}]: ").strip()
        return raw if raw else default
    else:
        return input(f"  {message}: ").strip()


def prompt_yes_no(message: str, default: bool = True) -> bool:
    """Prompt for yes/no with default."""
    hint = "Y/n" if default else "y/N"
    raw = input(f"  {message} [{hint}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


def prompt_secret(message: str, current: str = "") -> str:
    """Prompt for a secret value, showing masked current value if present."""
    if current and current not in PLACEHOLDERS:
        masked = current[:8] + "..." + current[-4:] if len(current) > 12 else "***"
        print(f"  Current: {masked}")
        if not prompt_yes_no("Change this value?", default=False):
            return current
    return prompt(message)


def run_pip(*args: str, quiet: bool = True) -> subprocess.CompletedProcess:
    """Run pip using the current Python interpreter."""
    cmd = [sys.executable, "-m", "pip"] + list(args)
    if quiet:
        cmd.append("-q")
    return subprocess.run(cmd, capture_output=quiet, text=True)


def is_package_installed(name: str) -> bool:
    """Check if a Python package is importable."""
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def parse_env_file(path: Path, include_commented: bool = False) -> OrderedDict:
    """Parse a .env file into an OrderedDict of key=value pairs.

    If include_commented is True, also parses commented-out KEY=value lines
    (useful for reading .env.example to get all possible keys).
    """
    env = OrderedDict()
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if include_commented:
                uncommented = stripped.lstrip("# ")
                if "=" in uncommented and uncommented[0].isalpha() and uncommented.split("=")[0].replace("_", "").isalnum():
                    key, _, value = uncommented.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key not in env:  # Don't overwrite active values
                        env[key] = value
            continue
        if "=" in stripped:
            key, _, value = stripped.partition("=")
            key = key.strip()
            # Remove surrounding quotes if present
            value = value.strip().strip("'\"")
            env[key] = value
    return env


def read_env_template(path: Path) -> list:
    """
    Read .env.example preserving structure.
    Returns list of (type, content) tuples:
      ("comment", "# some comment")
      ("commented_kv", "KEY=value")  — a commented-out key=value line
      ("blank", "")
      ("kv", "KEY=value")
    """
    lines = []
    if not path.exists():
        return lines
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append(("blank", ""))
        elif stripped.startswith("#"):
            # Check if this is a commented-out KEY=value (e.g. "# TELEGRAM_BOT_TOKEN=...")
            uncommented = stripped.lstrip("# ")
            if "=" in uncommented and uncommented[0].isalpha() and uncommented.split("=")[0].replace("_", "").isalnum():
                lines.append(("commented_kv", uncommented))
            else:
                lines.append(("comment", stripped))
        else:
            lines.append(("kv", stripped))
    return lines


def write_env_from_template(template_path: Path, output_path: Path, values: dict) -> None:
    """Write .env using the template structure, substituting values from the dict."""
    template = read_env_template(template_path)
    out_lines = []
    for kind, content in template:
        if kind in ("comment", "blank"):
            out_lines.append(content)
        elif kind in ("kv", "commented_kv"):
            key, _, _ = content.partition("=")
            key = key.strip()
            if key in values and values[key] and values[key] not in PLACEHOLDERS:
                out_lines.append(f"{key}={values[key]}")
            else:
                # Keep as commented-out placeholder
                out_lines.append(f"# {content}")
    output_path.write_text("\n".join(out_lines) + "\n")


def validate_telegram_token(token: str) -> bool:
    """Validate a Telegram bot token by calling getMe."""
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                bot_name = data.get("result", {}).get("username", "unknown")
                print_ok(f"Token valid (bot: @{bot_name})")
                return True
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        print_warn(f"Could not validate token: {e}")
    return False


def validate_slack_token(token: str) -> bool:
    """Validate a Slack bot token by calling auth.test."""
    try:
        url = "https://slack.com/api/auth.test"
        req = urllib.request.Request(url, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                team = data.get("team", "unknown")
                print_ok(f"Token valid (workspace: {team})")
                return True
            else:
                print_warn(f"Token invalid: {data.get('error', 'unknown error')}")
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        print_warn(f"Could not validate token: {e}")
    return False


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def step_check_prerequisites() -> None:
    """Step 1: Check Python version, pip, git."""
    print_step(1, "Checking prerequisites")

    # Python version
    v = sys.version_info
    if v >= MIN_PYTHON:
        print_ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        print(f"  [!!] Python {v.major}.{v.minor} found — requires {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+")
        sys.exit(1)

    # pip
    result = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        print_ok("pip available")
    else:
        print_warn("pip not available — install pip first")
        sys.exit(1)

    # git
    result = subprocess.run(["git", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        print_ok("git available")
    else:
        print_warn("git not found — needed to clone agentpool")

    # Node.js (optional, for claude setup-token)
    result = subprocess.run(["node", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        print_ok(f"Node.js {result.stdout.strip()} (needed for claude setup-token)")
    else:
        print_skip("Node.js not found (needed later for 'claude setup-token')")

    # uv (optional, for workspace scripts)
    result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        print_ok(f"uv {result.stdout.strip().split()[-1]} (needed for workspace scripts)")
    else:
        print_skip("uv not found (needed for workspace integration scripts)")


def step_install_agentpool() -> Path:
    """Step 2: Clone and install agentpool. Returns the install path."""
    print_step(2, "Installing agentpool")
    print_info("agentpool provides Claude SDK orchestration for NoClaw.")
    print()

    if is_package_installed("agentpool"):
        print_ok("agentpool already installed")
        # Return a dummy path since it's already installed
        return AGENTPOOL_DEFAULT_PATH

    # Ask where to clone
    default_path = str(AGENTPOOL_DEFAULT_PATH)
    path_str = prompt("Where should agentpool be cloned?", default=default_path)
    agentpool_path = Path(path_str).resolve()

    # Clone if not present
    if not agentpool_path.exists():
        print()
        print_info(f"Cloning {AGENTPOOL_REPO_URL} -> {agentpool_path}")
        result = subprocess.run(
            ["git", "clone", AGENTPOOL_REPO_URL, str(agentpool_path)],
            capture_output=False,
        )
        if result.returncode != 0:
            print_warn("Failed to clone agentpool")
            print_info("You can install it manually later:")
            print_info(f"  git clone {AGENTPOOL_REPO_URL} {agentpool_path}")
            print_info(f"  pip install -e {agentpool_path}")
            return agentpool_path
    else:
        print_ok(f"agentpool directory exists at {agentpool_path}")

    # Install
    print_info("Installing agentpool...")
    result = run_pip("install", "-e", str(agentpool_path), quiet=False)
    if result.returncode == 0:
        print_ok("agentpool installed")
    else:
        print_warn("Failed to install agentpool")
        print_info(f"Try manually: pip install -e {agentpool_path}")

    return agentpool_path


def step_install_deps() -> None:
    """Step 3: Install Python dependencies."""
    print_step(3, "Installing Python dependencies")

    if not REQUIREMENTS.exists():
        print_warn(f"Requirements file not found: {REQUIREMENTS}")
        return

    print_info(f"Installing from {REQUIREMENTS.relative_to(NOCLAW_ROOT)}...")
    result = run_pip("install", "-r", str(REQUIREMENTS), quiet=False)
    if result.returncode == 0:
        print_ok("Dependencies installed")
    else:
        print_warn("Some dependencies failed to install")
        print_info(f"Try manually: pip install -r {REQUIREMENTS.relative_to(NOCLAW_ROOT)}")


def step_configure_env() -> OrderedDict:
    """Step 4: Configure .env from .env.example. Returns the env values dict."""
    print_step(4, "Configuring environment")

    # Load existing values if .env exists
    existing = OrderedDict()
    if ENV_FILE.exists():
        existing = parse_env_file(ENV_FILE)
        # Back up
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = ENV_FILE.with_suffix(f".backup.{timestamp}")
        shutil.copy2(ENV_FILE, backup)
        print_ok(f"Backed up existing .env to {backup.name}")
        print()

    # Load template defaults
    template_values = parse_env_file(ENV_EXAMPLE, include_commented=True) if ENV_EXAMPLE.exists() else OrderedDict()

    # Merge: existing values take precedence over template
    values = OrderedDict()
    for key, val in template_values.items():
        values[key] = existing.get(key, val)

    # Also include any keys from existing .env not in template
    for key, val in existing.items():
        if key not in values:
            values[key] = val

    # --- Authentication ---
    print("  --- Authentication ---")
    print()
    current_token = values.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    if current_token and current_token not in PLACEHOLDERS:
        masked = current_token[:12] + "..." + current_token[-4:]
        print_ok(f"Claude OAuth token already set ({masked})")
        if prompt_yes_no("Change it?", default=False):
            print_info("Get your token by running 'claude setup-token' in a separate terminal.")
            values["CLAUDE_CODE_OAUTH_TOKEN"] = prompt("Claude OAuth Token")
    else:
        print_info("Get your token by running 'claude setup-token' in a separate terminal.")
        print_info("(You can skip this and add it to .env later)")
        token = prompt("Claude OAuth Token (Enter to skip)")
        if token:
            values["CLAUDE_CODE_OAUTH_TOKEN"] = token
    print()

    # --- Server ---
    print("  --- Server ---")
    values["PORT"] = prompt("Port", default=values.get("PORT", "3000"))
    values["DATA_DIR"] = prompt("Data directory", default=values.get("DATA_DIR", "data"))
    values["AGENT_TIMEOUT"] = prompt("Agent timeout (seconds)", default=values.get("AGENT_TIMEOUT", "300"))
    print()

    # --- Logging ---
    print("  --- Logging ---")
    values["LOG_LEVEL"] = prompt("Log level (DEBUG/INFO/WARNING/ERROR)", default=values.get("LOG_LEVEL", "INFO"))
    values["AGENT_LOG_FILE"] = prompt("Agent log file", default=values.get("AGENT_LOG_FILE", "data/agents.jsonl"))
    print()

    # --- Webhook Security ---
    print("  --- Webhook Security ---")
    current_key = values.get("NOCLAW_API_KEY", "")
    if current_key and current_key not in PLACEHOLDERS:
        print_ok("API key already set")
    else:
        print_info("Create a secret API key to require authentication on all NoClaw endpoints.")
        key = prompt("API key (Enter to skip, requests will be unauthenticated)")
        if key:
            values["NOCLAW_API_KEY"] = key

    return values


def step_setup_telegram(env: OrderedDict) -> None:
    """Step 5: Telegram channel setup (optional)."""
    print_step(5, "Telegram channel (optional)")

    # Check if already configured
    current_token = env.get("TELEGRAM_BOT_TOKEN", "")
    if current_token and current_token not in PLACEHOLDERS:
        print_ok("Telegram already configured")
        if not prompt_yes_no("Reconfigure?", default=False):
            return

    if not prompt_yes_no("Set up Telegram bot?", default=False):
        print_skip("Skipping Telegram")
        return

    print()
    print("  To create your Telegram bot:")
    print("    1. Open Telegram and search for @BotFather")
    print("    2. Send /newbot")
    print("    3. Choose a name (e.g. 'My Assistant') and username (e.g. 'my_noclaw_bot')")
    print("    4. BotFather will give you a token like 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    print()

    token = prompt("Bot token from BotFather")
    if not token:
        print_skip("No token provided, skipping Telegram")
        return

    # Validate token
    print()
    validate_telegram_token(token)

    print()
    print("  To get your Telegram user ID:")
    print("    1. Search for @userinfobot on Telegram")
    print("    2. Send /start")
    print("    3. It will reply with your numeric user ID")
    print()

    user_id = prompt("Your Telegram user ID")
    if not user_id:
        print_skip("No user ID provided, skipping Telegram")
        return

    model = prompt("Default model (haiku/sonnet/opus)", default="sonnet")

    env["TELEGRAM_BOT_TOKEN"] = token
    env["TELEGRAM_USER_ID"] = user_id
    env["TELEGRAM_MODEL_HINT"] = model

    # Install dependency if needed
    if not is_package_installed("telegram"):
        print()
        if prompt_yes_no("Install python-telegram-bot?", default=True):
            run_pip("install", "python-telegram-bot", quiet=False)

    print_ok("Telegram configured")


def step_setup_slack(env: OrderedDict) -> None:
    """Step 6: Slack channel setup (optional)."""
    print_step(6, "Slack channel (optional)")

    # Check if already configured
    current_token = env.get("SLACK_BOT_TOKEN", "")
    if current_token and current_token not in PLACEHOLDERS:
        print_ok("Slack already configured")
        if not prompt_yes_no("Reconfigure?", default=False):
            return

    if not prompt_yes_no("Set up Slack bot?", default=False):
        print_skip("Skipping Slack")
        return

    print()
    print("  To create your Slack bot:")
    print("    1. Go to https://api.slack.com/apps and click 'Create New App'")
    print("    2. Choose 'From scratch'")
    print("    3. Give it a name (e.g. 'NoClaw Assistant') and select your workspace")
    print("    4. Click 'Create App'")
    print()
    print("  Enable Socket Mode (lets the bot connect without a public URL):")
    print("    1. In the left sidebar, click 'Socket Mode'")
    print("    2. Toggle 'Enable Socket Mode' to ON")
    print("    3. Give the token a name like 'noclaw-socket' and click 'Generate'")
    print("    4. Copy the App-Level Token (starts with xapp-)")
    print()

    app_token = prompt("App-Level Token (starts with xapp-)")
    if not app_token:
        print_skip("No token provided, skipping Slack")
        return

    print()
    print("  Set up permissions and install the bot:")
    print("    1. Go to 'OAuth & Permissions'")
    print("    2. Under 'Bot Token Scopes', add:")
    print("       app_mentions:read, chat:write, files:read, im:history, im:read, im:write")
    print("    3. Click 'Install to Workspace', then 'Allow'")
    print("    4. Copy the Bot User OAuth Token (starts with xoxb-)")
    print()

    bot_token = prompt("Bot User OAuth Token (starts with xoxb-)")
    if not bot_token:
        print_skip("No token provided, skipping Slack")
        return

    # Validate bot token
    print()
    validate_slack_token(bot_token)

    print()
    print("  Subscribe to events:")
    print("    1. Go to 'Event Subscriptions' and toggle ON")
    print("    2. Under 'Subscribe to bot events', add: app_mention, message.im")
    print("    3. Click 'Save Changes'")
    print("    4. Go back to 'OAuth & Permissions' and click 'Reinstall to Workspace'")
    print()
    print("  Enable DMs:")
    print("    1. Go to 'App Home'")
    print("    2. Toggle 'Messages Tab' ON")
    print("    3. Check 'Allow users to send Slash commands and messages from the messages tab'")
    print()
    print("  Get your Slack user ID:")
    print("    1. Click your profile picture -> Profile -> three dots (...) -> Copy member ID")
    print()

    user_id = prompt("Your Slack member ID (starts with U)")

    model = prompt("Default model (haiku/sonnet/opus)", default="sonnet")

    env["SLACK_BOT_TOKEN"] = bot_token
    env["SLACK_APP_TOKEN"] = app_token
    if user_id:
        env["SLACK_USER_ID"] = user_id
    env["SLACK_MODEL_HINT"] = model

    # Install dependency if needed
    if not is_package_installed("slack_bolt"):
        print()
        if prompt_yes_no("Install slack-bolt?", default=True):
            run_pip("install", "slack-bolt", quiet=False)

    print_ok("Slack configured")


def step_setup_google(env: OrderedDict) -> None:
    """Step 7: Google integrations setup (optional)."""
    print_step(7, "Google integrations (optional)")

    # Check if already configured
    if GOOGLE_TOKEN_FILE.exists():
        print_ok("Google OAuth token exists")
        if not prompt_yes_no("Reconfigure?", default=False):
            # Still collect calendar ID if missing
            if not env.get("GOOGLE_CALENDAR_ID"):
                cal_id = prompt("Google Calendar ID (Enter to skip)")
                if cal_id:
                    env["GOOGLE_CALENDAR_ID"] = cal_id
            _install_workspace_scripts()
            return

    if not prompt_yes_no("Set up Google integrations (Gmail, Calendar, Sheets, Docs, Drive)?", default=False):
        print_skip("Skipping Google integrations")
        _install_workspace_scripts()
        return

    # Auto-migrate credentials from old location
    if not GOOGLE_CREDENTIALS_FILE.exists() and OLD_GOOGLE_CREDENTIALS.exists():
        print_info(f"Found credentials at old location, moving to project root...")
        shutil.copy2(OLD_GOOGLE_CREDENTIALS, GOOGLE_CREDENTIALS_FILE)
        print_ok("Migrated google_credentials.json to project root")
    if not GOOGLE_TOKEN_FILE.exists() and OLD_GOOGLE_TOKEN.exists():
        shutil.copy2(OLD_GOOGLE_TOKEN, GOOGLE_TOKEN_FILE)
        print_ok("Migrated google_token.json to project root")
        # If we migrated both, we're done with OAuth
        if GOOGLE_TOKEN_FILE.exists():
            print_ok("Google OAuth already authenticated (migrated from old location)")
            cal_id = prompt("Google Calendar ID (Enter to skip)", default=env.get("GOOGLE_CALENDAR_ID", ""))
            if cal_id:
                env["GOOGLE_CALENDAR_ID"] = cal_id
            _install_workspace_scripts()
            return

    # Guide user through Google Cloud Console setup
    print()
    print("  To set up Google OAuth:")
    print("    1. Go to https://console.cloud.google.com")
    print("    2. Create or select a project")
    print("    3. Enable these APIs (search each in the top bar, click Enable):")
    print("       - Gmail API")
    print("       - Google Calendar API")
    print("    4. Go to 'APIs & Services' -> 'OAuth consent screen'")
    print("       - User type: 'External'")
    print("       - Fill in app name and support email, save")
    print("       - Click 'Publish App' to move to Production")
    print("         (avoids 7-day token expiry)")
    print("    5. Go to 'APIs & Services' -> 'Credentials' -> 'Create Credentials'")
    print("       -> 'OAuth client ID'")
    print("       - Application type: 'Desktop app'")
    print("       - Download the JSON file")
    print(f"       - Save as: {GOOGLE_CREDENTIALS_FILE.name} (in this directory)")
    print()

    if not GOOGLE_CREDENTIALS_FILE.exists():
        input("  Press Enter when ready (or Ctrl+C to skip)...")
        print()

    if not GOOGLE_CREDENTIALS_FILE.exists():
        print_warn(f"{GOOGLE_CREDENTIALS_FILE.name} not found in project root")
        print_info("You can re-run setup.py later after downloading it.")
        _install_workspace_scripts()
        return

    print_ok(f"Found {GOOGLE_CREDENTIALS_FILE.name}")

    # Collect Calendar ID
    cal_id = prompt("Google Calendar ID (Enter to skip)", default=env.get("GOOGLE_CALENDAR_ID", ""))
    if cal_id:
        env["GOOGLE_CALENDAR_ID"] = cal_id

    # Install Google auth dependencies
    print()
    print_info("Installing Google auth dependencies...")
    result = run_pip("install", "google-auth-oauthlib", "google-api-python-client", quiet=False)
    if result.returncode != 0:
        print_warn("Failed to install Google auth dependencies")
        print_info("Try manually: pip install google-auth-oauthlib google-api-python-client")
        return

    # Run OAuth flow
    print()
    headless = not prompt_yes_no("Open browser for OAuth? (say No for headless/remote)", default=True)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(
            str(GOOGLE_CREDENTIALS_FILE), GOOGLE_SCOPES
        )

        if headless:
            flow.redirect_uri = "http://localhost:1"
            auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
            print()
            print("  Open this URL in your browser:")
            print(f"  {auth_url}")
            print()
            print("  Authorize the app. You'll be redirected to a page that FAILS to load.")
            print("  That's expected! Copy the FULL URL from your browser's address bar.")
            print()
            redirect_response = input("  Paste the full redirect URL here: ").strip()
            flow.fetch_token(authorization_response=redirect_response)
            creds = flow.credentials
        else:
            creds = flow.run_local_server(port=0)

        # Save token
        GOOGLE_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        print_ok(f"Token saved to {GOOGLE_TOKEN_FILE.name}")

        # Validate
        from googleapiclient.discovery import build

        gmail = build("gmail", "v1", credentials=creds)
        profile = gmail.users().getProfile(userId="me").execute()
        print_ok(f"Gmail connected as {profile.get('emailAddress', '?')}")

        calendar = build("calendar", "v3", credentials=creds)
        cal_list = calendar.calendarList().list(maxResults=1).execute()
        print_ok(f"Calendar access confirmed ({len(cal_list.get('items', []))} calendars visible)")

    except KeyboardInterrupt:
        print()
        print_skip("OAuth flow cancelled")
    except Exception as e:
        print_warn(f"OAuth flow failed: {e}")
        print_info("You can re-run setup.py later to try again.")

    # Install workspace script dependencies via uv
    _install_workspace_scripts()


def _install_workspace_scripts() -> None:
    """Install workspace script dependencies using uv sync."""
    scripts_dir = NOCLAW_ROOT / "workspace" / ".claude" / "scripts"
    if not (scripts_dir / "pyproject.toml").exists():
        return

    print()
    print_info("Installing workspace script dependencies...")

    uv_path = shutil.which("uv")
    if not uv_path:
        print_warn("uv not found — workspace scripts need it for dependency management")
        print_info("Install uv: https://docs.astral.sh/uv/getting-started/installation/")
        print_info(f"Then run: cd {scripts_dir.relative_to(NOCLAW_ROOT)} && uv sync")
        return

    result = subprocess.run(
        [uv_path, "sync"],
        cwd=str(scripts_dir),
        capture_output=False,
    )
    if result.returncode == 0:
        print_ok("Workspace scripts installed")
    else:
        print_warn("Failed to install workspace scripts")
        print_info(f"Try manually: cd {scripts_dir.relative_to(NOCLAW_ROOT)} && uv sync")


def step_write_env(env: OrderedDict) -> None:
    """Step 8: Write .env file."""
    print_step(8, "Writing .env")

    if ENV_EXAMPLE.exists():
        write_env_from_template(ENV_EXAMPLE, ENV_FILE, env)
    else:
        # Fallback: write key=value pairs directly
        lines = []
        for key, value in env.items():
            if value and value not in PLACEHOLDERS:
                lines.append(f"{key}={value}")
            else:
                lines.append(f"# {key}=")
        ENV_FILE.write_text("\n".join(lines) + "\n")

    # Count configured values
    configured = sum(1 for v in env.values() if v and v not in PLACEHOLDERS)
    print_ok(f".env written ({configured} values configured)")


def step_verify() -> None:
    """Step 9: Verify installation."""
    print_step(9, "Verification")

    # Python
    v = sys.version_info
    print_ok(f"Python {v.major}.{v.minor}")

    # agentpool
    if is_package_installed("agentpool"):
        print_ok("agentpool installed")
    else:
        print_warn("agentpool not installed")

    # FastAPI
    if is_package_installed("fastapi"):
        print_ok("FastAPI installed")
    else:
        print_warn("FastAPI not installed")

    # .env
    if ENV_FILE.exists():
        print_ok(".env file exists")
    else:
        print_warn(".env file missing")

    # Token
    env = parse_env_file(ENV_FILE) if ENV_FILE.exists() else {}
    token = env.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    if token and token not in PLACEHOLDERS:
        print_ok("CLAUDE_CODE_OAUTH_TOKEN set")
    else:
        print_warn("CLAUDE_CODE_OAUTH_TOKEN not set — add it before running")

    # Channels
    if env.get("TELEGRAM_BOT_TOKEN") and env["TELEGRAM_BOT_TOKEN"] not in PLACEHOLDERS:
        print_ok("Telegram configured")
    if env.get("SLACK_BOT_TOKEN") and env["SLACK_BOT_TOKEN"] not in PLACEHOLDERS:
        print_ok("Slack configured")

    # Google
    if GOOGLE_TOKEN_FILE.exists():
        print_ok("Google OAuth configured")

    # Workspace scripts
    scripts_venv = NOCLAW_ROOT / "workspace" / ".claude" / "scripts" / ".venv"
    if scripts_venv.exists():
        print_ok("Workspace scripts installed")
    else:
        print_warn("Workspace scripts not installed (run: cd workspace/.claude/scripts && uv sync)")


def print_next_steps() -> None:
    """Print post-setup instructions."""
    print_header("Setup complete!")

    env = parse_env_file(ENV_FILE) if ENV_FILE.exists() else {}
    token = env.get("CLAUDE_CODE_OAUTH_TOKEN", "")

    step = 1
    if not token or token in PLACEHOLDERS:
        print(f"  {step}. Add your Claude OAuth token to .env:")
        print("     Run 'claude setup-token' in a separate terminal")
        print("     Then paste the token into .env as CLAUDE_CODE_OAUTH_TOKEN=...")
        print()
        step += 1

    print(f"  {step}. Start the server:")
    print("     python run_assistant.py")
    print()
    step += 1

    print(f"  {step}. Test with curl:")
    print('     curl -X POST http://localhost:3000/webhook \\')
    print('       -H "Content-Type: application/json" \\')
    print("       -d '{\"user\": \"test\", \"message\": \"Hello!\"}'")
    print()
    step += 1

    print(f"  {step}. View the dashboard:")
    print("     http://localhost:3000/dashboard")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print_header("NoClaw Setup")

    step_check_prerequisites()
    step_install_agentpool()
    step_install_deps()
    env = step_configure_env()
    step_setup_telegram(env)
    step_setup_slack(env)
    step_setup_google(env)
    step_write_env(env)
    step_verify()
    print_next_steps()


if __name__ == "__main__":
    main()
