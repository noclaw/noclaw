---
name: terminal-control
description: Run shell commands, manage long-running processes, and spawn sub-agents via the terminal. Use for system tasks, installing software, running scripts, file management, process monitoring, and any task that requires shell access. Triggers on requests like "run this command", "install this", "check disk space", "what processes are running", "restart the service", "manage files".
---

# Terminal Control

Run shell commands, manage processes, and spawn sub-agents via the terminal.

## Running Commands

You have direct shell access. Run commands normally:

```bash
# System info
uname -a                       # Kernel info
df -h                          # Disk space
top -l 1 | head -20            # CPU/memory snapshot
```

## Long-Running Processes with tmux

For commands that take a while or need to run in the background, use tmux:

```bash
# Start a named session for a long task
tmux new-session -d -s mytask "python long_script.py"

# Check on it
tmux capture-pane -t mytask -p     # See current output

# List running sessions
tmux list-sessions

# Stop a task
tmux kill-session -t mytask
```

### Run and Monitor Pattern

```bash
# Start a background task
tmux new-session -d -s download "curl -L -o files/data.zip https://example.com/large-file.zip"

# Check progress periodically
tmux capture-pane -t download -p

# When done, clean up
tmux kill-session -t download
```

## File Management

```bash
# Workspace files
ls files/                      # List user files
mkdir -p files/reports         # Create directories

# Move, copy, compress
cp source.txt files/backup.txt
tar -czf files/archive.tar.gz files/reports/
zip -r files/output.zip files/data/

# Find files
find files/ -name "*.pdf" -mtime -7    # PDFs modified in last 7 days
du -sh files/*                          # Directory sizes
```

## Process Management

```bash
# Find processes
ps aux | grep python
pgrep -l "node\|python"

# Kill processes
kill <pid>                     # Graceful
kill -9 <pid>                  # Force

# Ports
lsof -i :3000                 # What's using port 3000
```

## Package Management

```bash
# Node.js / npm
npm install -g <package>
npm list -g --depth=0

# Python / pip
pip install <package>
pip list
python -m venv .venv && source .venv/bin/activate
```

## Network

```bash
# HTTP requests
curl -s https://api.example.com/data | jq .
curl -X POST -H "Content-Type: application/json" -d '{"key":"value"}' https://api.example.com

# DNS / connectivity
ping -c 3 example.com
dig example.com
nslookup example.com

# Download files
curl -L -o files/download.zip https://example.com/file.zip
```

## Reliable tmux Completion (Sentinel Protocol)

To know exactly when a tmux command finishes and whether it succeeded, wrap it with sentinel markers:

```bash
# Generate a unique token
TOKEN=$(openssl rand -hex 4)

# Run command with sentinels
tmux send-keys -t mytask "echo __START_${TOKEN} ; npm test ; echo __DONE_${TOKEN}:\$?" Enter

# Later, check for completion
tmux capture-pane -t mytask -p | grep "__DONE_${TOKEN}"
# Output: __DONE_a1b2c3d4:0   (exit code 0 = success)
```

This avoids guessing whether a command is still running or has finished.

## Agent Orchestration

You can spawn sub-agents in tmux sessions for parallel or complex workflows:

```bash
# Spawn a sub-agent for a focused task
tmux new-session -d -s research "claude -p 'Research the latest Python 3.13 features and write a summary to /tmp/python-summary.md'"

# Monitor progress
tmux capture-pane -t research -p

# Collect results when done (check for sentinel or process exit)
tmux capture-pane -t research -p | tail -5
cat /tmp/python-summary.md

# Clean up
tmux kill-session -t research
```

### Parallel sub-agents
```bash
# Spawn multiple focused agents
tmux new-session -d -s task1 "claude -p 'Research topic A, save to /tmp/a.md'"
tmux new-session -d -s task2 "claude -p 'Research topic B, save to /tmp/b.md'"

# Wait for both, then synthesize
# (check tmux list-sessions to see when they exit)
```

Always clean up sub-agent tmux sessions when done.

## Tips

- **Use tmux for anything slow** — don't block on long downloads or builds
- **Use `jq` for JSON** — pipe curl output through jq for readable results
