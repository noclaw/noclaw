# NoClaw Quick Start Guide

## Setup Options

NoClaw provides multiple ways to get started:

1. **Automated Setup** - Run `./setup.sh` for one-command setup
   - Installs Python dependencies
   - Builds Docker container
   - Creates `.env` template
   - ✅ **Recommended for most users**

2. **Manual Setup** - Follow the step-by-step instructions below
   - Understand each step
   - Better for debugging issues
   - ✅ **Recommended if setup.sh fails**

3. **Validation** - Run `python run_assistant.py` (no `--skip-validation` flag)
   - Runs `server/startup.py` checks before starting
   - Validates Docker, Python, token, disk space
   - Reports clear error messages
   - ✅ **Always enabled by default**

**Note:** The OAuth token step is always manual - you need to run `claude setup-token` in a separate terminal and copy the token.

---

## Prerequisites

1. **Claude.ai Subscription** 
   - Pro or Max subscription at https://claude.ai
   - You'll get an OAuth token via Claude Code CLI

2. **Node.js** (Required for Claude Code CLI)
   - To install the Claude Code CLI
   - `npm` command must be available

3. **Docker or Podman** (Recommended)
   - For container isolation and security
   - Can run without it using `--local` flag

4. **Python 3.11+** (Required)
   - For running the assistant server

## Step 1: Get Your Claude Token

The Claude SDK requires authentication. You need a `CLAUDE_CODE_OAUTH_TOKEN`.

### Install Claude Code CLI
```bash
npm install -g @anthropic-ai/claude-code
```

### Get Your OAuth Token
```bash
claude setup-token
```

This command will:
1. Open your browser to authorize Claude Code
2. Display your OAuth token in the terminal (valid for 1 year)
3. Show a token that starts with `sk-ant-oat01-`

Copy the entire token - you'll need it for the next step.

## Step 2: Setup NoClaw

### Option A: Automated (Recommended)

```bash
# Clone the repository (if not already done)
git clone <repo-url>
cd noclaw

# Run setup script
./setup.sh

# Edit .env and add your token
nano .env
```

### Option B: Manual Steps

```bash
# Install Python dependencies
pip3 install -r server/requirements.txt

# Build Docker container
./build_worker.sh

# Create .env file
cp .env.example .env
nano .env
```

### Configure .env

Add this line to your `.env` file:
```
CLAUDE_CODE_OAUTH_TOKEN='your-actual-token-here'
```

## Step 3: Run the Assistant

### With Docker (Recommended)
```bash
# Make sure your token is set
source .env

# Build and run
./build_worker.sh
python run_assistant.py
```

### Without Docker (Local Mode)
```bash
# Install Claude Code CLI first
npm install -g @anthropic-ai/claude-code

# Run locally
source .env
python run_assistant.py --local
```

## Step 4: Test It

```bash
# Simple test
curl -X POST http://localhost:3000/webhook \
  -H "Content-Type: application/json" \
  -d '{"user": "test", "message": "What is 2+2?"}'

# Should return a real response like:
# {"response": "2 + 2 = 4", ...}
```

## Troubleshooting

### "Invalid API key" Error
- Make sure `CLAUDE_CODE_OAUTH_TOKEN` is set in `.env`
- Run `source .env` before starting the assistant
- Check the token is valid and not expired

### "Control request timeout: initialize" Error
- The Claude SDK couldn't start properly
- Make sure Node.js is available (should be in container)
- Check Docker logs: `docker logs <container-id>`

### Container Build Fails
- Make sure you have internet connection
- npm registry must be accessible
- Try: `docker system prune` to clean up

### "exit code -9" or SIGKILL Errors
- The Claude CLI requires at least 1GB of memory
- Default is now set to 1GB in `.env`
- If still failing, increase `CONTAINER_MEMORY_LIMIT` in `.env`

### No Docker Available
- Use local mode: `python run_assistant.py --local`
- Must have Claude Code CLI installed locally
- Run: `npm install -g @anthropic-ai/claude-code`

## Next Steps

Once working, you can:
1. Schedule tasks with cron expressions
2. Customize per-user instructions
3. Add new communication channels
4. Let Claude Code modify the system for your needs

## Getting Real Claude Responses

The system is designed to give you **real Claude SDK responses** from the start. No mocks or simulations. If you see mock-like responses, it means:
1. Token is not set properly
2. SDK couldn't authenticate
3. Container couldn't connect to Claude API

Always check:
```bash
echo $CLAUDE_CODE_OAUTH_TOKEN  # Should show your token
docker logs <container-id>      # Check for errors
```