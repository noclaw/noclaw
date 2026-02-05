---
name: setup
description: Run initial NoClaw setup. Builds the Docker container, configures authentication, and starts the assistant. Use when user wants to install dependencies or set up NoClaw for the first time.
---

# NoClaw Setup

This skill helps you set up NoClaw - a minimal, containerized Claude assistant that prioritizes security and simplicity.

## 1. Check Prerequisites

```bash
# Check Python
python --version || python3 --version

# Check Docker
docker --version
```

If Docker isn't installed, tell the user:
> Please install Docker Desktop from https://docker.com/products/docker-desktop
> Let me know when you've completed the installation.

## 2. Configure Claude Authentication

Check if .env exists:
```bash
if [ -f .env ]; then
  echo ".env file already exists"
  grep -q "CLAUDE_CODE_OAUTH_TOKEN" .env && echo "OAuth token configured" || echo "No OAuth token"
  grep -q "ANTHROPIC_API_KEY" .env && echo "API key configured" || echo "No API key"
else
  echo ".env file not found"
fi
```

If .env doesn't exist, create it from the example:
```bash
cp .env.example .env
```

Ask the user:
> Do you want to use your **Claude subscription** (Pro/Max) or an **Anthropic API key**?

### Option 1: Claude Subscription (Recommended)

First, check if Claude Code CLI is installed:
```bash
which claude && echo "Claude Code CLI is installed" || echo "Claude Code CLI not found"
```

If not installed, install it:
```bash
npm install -g @anthropic-ai/claude-code
```

Tell the user:
> I'll help you get your OAuth token using the Claude Code CLI.
>
> Run the following command:
> ```bash
> claude setup-token
> ```
>
> This will:
> 1. Open your browser to authorize Claude Code
> 2. Display your OAuth token in the terminal (valid for 1 year)
>
> Copy the token (starts with `sk-ant-oat01-`) and paste it here.

Use the AskUserQuestion tool to get the token from the user, then:
```bash
# Update the .env file with the token
TOKEN="<user's token>"
if grep -q "^CLAUDE_CODE_OAUTH_TOKEN=" .env; then
  sed -i '' "s|^CLAUDE_CODE_OAUTH_TOKEN=.*|CLAUDE_CODE_OAUTH_TOKEN=$TOKEN|" .env
else
  echo "CLAUDE_CODE_OAUTH_TOKEN=$TOKEN" >> .env
fi
echo "✓ Token configured: ${TOKEN:0:20}...${TOKEN: -4}"
```

### Option 2: API Key

Tell the user:
> Please get your API key from https://console.anthropic.com/settings/keys
> Enter your API key:

Use the AskUserQuestion tool to get the API key, then:
```bash
# Update the .env file with the API key
API_KEY="<user's API key>"
if grep -q "^ANTHROPIC_API_KEY=" .env; then
  sed -i '' "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$API_KEY|" .env
else
  echo "ANTHROPIC_API_KEY=$API_KEY" >> .env
fi
echo "✓ API key configured"
```

## 3. Build the Worker Container

```bash
./build_worker.sh
```

This builds the Docker image with Claude SDK and all dependencies.

## 4. Test the Setup

```bash
python tests/test_real_claude.py
```

If tests pass, tell the user:
> ✅ NoClaw is successfully set up! The assistant is ready to use.
>
> To start the server: `python run_assistant.py`
>
> The API will be available at http://localhost:3000
>
> You can test it with:
> ```bash
> curl -X POST http://localhost:3000/webhook \
>   -H "Content-Type: application/json" \
>   -d '{"user": "test", "message": "Hello!"}'
> ```

## 5. Optional: Start the Server

Ask the user:
> Would you like me to start the assistant server now?

If yes:
```bash
python run_assistant.py &
sleep 3
curl -s http://localhost:3000/health | jq .
```

Tell the user:
> The assistant is now running in the background at http://localhost:3000
>
> To stop it later, run: `pkill -f "python run_assistant.py"`