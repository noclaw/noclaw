---
name: terminal-control
description: Run shell commands, manage long-running processes, and control the Mac via the terminal. Use for system tasks, installing software, running scripts, file management, process monitoring, and any task that requires shell access. Triggers on requests like "run this command", "install this", "check disk space", "what processes are running", "restart the service", "manage files".
---

# Terminal Control

Run shell commands, manage processes, and control the Mac via the terminal.

## Running Commands

You have direct shell access. Run commands normally:

```bash
# System info
sw_vers                        # macOS version
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

## macOS-Specific

```bash
# Open apps
open -a "Safari"
open -a "Finder" ~/Documents
open https://example.com       # Open URL in default browser

# Clipboard
pbcopy < file.txt             # Copy file to clipboard
pbpaste > output.txt          # Paste clipboard to file

# Notifications
osascript -e 'display notification "Done!" with title "Task Complete"'

# System preferences
open "x-apple.systempreferences:com.apple.preference.security"

# Screenshots (alternative to agent-browser)
screencapture -x files/screen.png          # Silent screenshot
screencapture -x -R 0,0,800,600 files/region.png  # Region
```

## Package Management

```bash
# Homebrew
brew install <package>
brew list
brew update && brew upgrade

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

## Tips

- **Save output to files/** — keep results in the workspace for later reference
- **Use tmux for anything slow** — don't block on long downloads or builds
- **Prefer `files/` for all output** — screenshots, reports, downloads all go here
- **Use `jq` for JSON** — pipe curl output through jq for readable results
