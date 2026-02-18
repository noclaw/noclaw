# Security Model

## Overview

NoClaw provides security through two layers:

1. **Workspace isolation** — SecurityPolicy validates paths, each user gets a separate workspace
2. **Optional Docker sandboxing** — shell commands execute inside containers when `SANDBOX_TYPE=docker`

The default mode (`SANDBOX_TYPE=local`) runs agents directly on the host. This is fast and suitable for single-user or development setups. Docker sandboxing adds container isolation for shell commands when needed.

## Workspace Isolation

### Key Principle

**Each user's workspace is isolated. Agent access is restricted to the user's workspace directory.**

```
data/workspaces/
├── alice/
│   ├── CLAUDE.md        # Alice's instructions
│   ├── memory.md        # Alice's persistent facts
│   ├── files/           # Alice's files
│   └── conversations/   # Alice's archived conversations
├── bob/
│   └── ...              # Bob's separate workspace
└── telegram_12345/
    └── ...              # Telegram user's workspace
```

### SecurityPolicy

The `SecurityPolicy` class in [server/security.py](../server/security.py) validates all workspace paths:

- Workspaces must be under `DATA_DIR/workspaces/`
- System directories (`/etc`, `/var`, `/sys`, `/usr`) are blocked
- Sensitive patterns are blocked: `.ssh`, `.aws`, `.env`, `.git/config`, `credentials`, `secrets`
- Clear error messages explain why paths are rejected

```python
# In assistant.py — workspace paths validated before use
from .security import SecurityPolicy
if not SecurityPolicy().validate_workspace(Path(workspace_path)):
    raise ValueError(f"Workspace path rejected by security policy: {workspace_path}")
```

### Blocked Patterns

These patterns are never allowed in workspace paths:

- `.ssh` — SSH keys and config
- `.aws` — AWS credentials
- `.env` — Environment files with secrets
- `.git/config` — Git credentials
- `credentials` — Generic credential files
- `secrets` — Secret files
- `node_modules` — Large dependency directories
- `.venv` — Python virtual environments
- `__pycache__` — Python cache files

## Sandbox Modes

NoClaw uses [agentpool](https://github.com/noclaw/agentpool) for agent execution. The sandbox type controls how shell commands run:

### Local Sandbox (Default)

```bash
python run_assistant.py          # or --local
```

- Agent runs on the host, shell commands execute directly
- Fast, no container overhead
- Suitable for single-user setups and development
- The Claude SDK runs with the same permissions as the NoClaw process

### Docker Sandbox

```bash
python run_assistant.py --docker
```

- Agent runs on the host, shell commands execute inside a Docker container
- User workspace mounted at `/workspace` inside the container
- Container runs with `--security-opt no-new-privileges`
- Resource limits: memory, CPU, timeouts configurable via agentpool

Docker containers provide:
- Filesystem isolation — agent can only see `/workspace`
- Process isolation — cannot affect host processes
- Network control — configurable per container
- Resource limits — memory and CPU caps

## Webhook Authentication

### API Key Protection

Set `NOCLAW_API_KEY` in `.env` to require authentication on all endpoints:

```bash
NOCLAW_API_KEY=your-secret-key-here
```

Clients authenticate via:
- `X-API-Key: your-secret-key` header
- `Authorization: Bearer your-secret-key` header

If `NOCLAW_API_KEY` is unset, all requests are allowed (development mode).

### Channel Authentication

Each channel plugin handles its own authentication:
- **Telegram** — `TELEGRAM_USER_ID` restricts which Telegram users can interact
- **Slack** — `SLACK_USER_ID` restricts which Slack users can interact

## Testing Security

```bash
# Run the security test suite
python3 tests/test_security.py
```

Tests verify:
- Valid workspaces are accepted
- Invalid workspaces are rejected
- Blocked patterns are caught
- Additional mount validation works
- Config loading works

## Best Practices

1. **Set `NOCLAW_API_KEY`** in production to protect webhook endpoints
2. **Use Docker sandbox** when running untrusted or multi-user workloads
3. **Restrict channel users** — set `TELEGRAM_USER_ID` / `SLACK_USER_ID` to your IDs only
4. **Don't commit `.env`** — it contains secrets
5. **Review workspace contents** periodically — users can upload files via channels
