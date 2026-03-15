# Security Model

## Overview

NoClaw provides security through two layers:

1. **Workspace isolation** — SecurityPolicy validates paths, agent runs in a shared workspace
2. **Container deployment** — Run NoClaw in a Docker container for production isolation

The default mode runs agents directly on the host. This is fast and suitable for single-user or development setups. For production, run the entire NoClaw server in a Docker container to achieve isolation.

## Workspace Isolation

### Key Principle

**Agent access is restricted to the shared workspace directory.**

```
workspace/                     # Shared agent workspace
├── .claude/                   # Agent-specific Claude config
│   └── skills/                # Skills available to the agent
├── CLAUDE.md                  # Agent instructions (regenerated each run)
├── TASKS-HEARTBEAT.md         # Heartbeat checklist (optional)
├── files/                     # User files
└── conversations/             # Archived conversations
```

### SecurityPolicy

The `SecurityPolicy` class in [server/security.py](../server/security.py) validates all workspace paths:

- Workspaces must be under the configured workspace root (`workspace/`)
- System directories (`/etc`, `/var`, `/sys`, `/usr`) are blocked
- Sensitive patterns are blocked: `.ssh`, `.aws`, `.env`, `.git/config`, `credentials`, `secrets`
- Clear error messages explain why paths are rejected

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

## Production Isolation

For production, run NoClaw in a Docker container. The container itself provides the isolation boundary:

```bash
docker-compose up -d
```

The Docker container:
- Runs as a non-root user
- Only mounts `data/` and `workspace/` directories
- Uses local execution inside the container (no Docker-in-Docker)
- Provides filesystem, process, and network isolation

See [DEPLOY.md](DEPLOY.md) for deployment details.

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

## Dashboard Authentication

Set `NOCLAW_PASSWORD` in `.env` to require a password for the web dashboard at `/dashboard`. When set, users must log in before accessing the dashboard, SSE stream, or test endpoint. An HTTP-only session cookie is set on successful login.

When `NOCLAW_PASSWORD` is unset, the dashboard is open (suitable for local/dev use).

For production deployments exposed to the internet, use Nginx basic auth or IP allowlisting as an additional layer. See [DIGITAL-OCEAN-SETUP.md](DIGITAL-OCEAN-SETUP.md) for a complete example.

## Best Practices

1. **Set `NOCLAW_API_KEY`** in production to protect webhook/API endpoints
2. **Set `NOCLAW_PASSWORD`** to protect the dashboard when exposed publicly
3. **Run in Docker** for production isolation
4. **Restrict channel users** — set `TELEGRAM_USER_ID` / `SLACK_USER_ID` to your IDs only
5. **Don't commit `.env`** — it contains secrets
6. **Review workspace contents** periodically — users can upload files via channels
