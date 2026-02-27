# Deployment Guide

## Deployment Model

NoClaw is a single Python process that uses [agentpool](https://github.com/noclaw/agentpool) for Claude SDK orchestration. For production, the recommended pattern is:

**Containerize the host application (including agentpool) and use `LocalSandbox` — the platform container provides the isolation boundary.**

There is no separate worker container. The Claude SDK runs inside the same process as the FastAPI server.

```
Docker Host
└── noclaw container
    ├── FastAPI server
    ├── agentpool (Claude SDK)
    ├── Channel plugins (Telegram, Slack)
    ├── data/ (mounted volume)
    └── workspace/ (mounted volume)
```

## Deployment Options

### Option 1: Native Python (Development)

Run directly on the host. Simplest setup.

```bash
pip install -r server/requirements.txt
pip install -e /path/to/agentpool[sdk]
python run_assistant.py
```

### Option 2: Docker Container (Production)

Build and run with Docker Compose:

```bash
# Configure
cp .env.example .env
nano .env  # Add CLAUDE_CODE_OAUTH_TOKEN

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Check health
curl http://localhost:3000/health
```

## Docker Configuration

### Dockerfile.server

The [Dockerfile.server](../Dockerfile.server) builds a container with:
- Python 3.11
- NoClaw server code
- agentpool installed from GitHub
- Claude Code CLI (via Node.js)
- Non-root user

### docker-compose.yml

The [docker-compose.yml](../docker-compose.yml) provides:
- Data and workspace persistence via volume mounts
- Google credential files mounted read-only (if present)
- Health checks with auto-restart
- Log rotation (10MB, 3 files)
- Port mapping (default 3000)
- Environment from `.env` file

**Key:** No Docker socket mount is needed. Shell commands run directly inside the container, which is already isolated.

## Environment Variables

Required:
```bash
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...   # Claude authentication
```

Optional:
```bash
PORT=3000                    # Server port
DATA_DIR=data                # Data directory
LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR
AGENT_LOG_FILE=data/agents.jsonl  # Agent performance logs
AGENT_TIMEOUT=300            # Agent timeout in seconds
TIMEZONE=America/Denver      # Timezone for Gmail/Calendar integrations
NOCLAW_API_KEY=secret        # Webhook authentication

# Channel plugins
TELEGRAM_BOT_TOKEN=...
TELEGRAM_USER_ID=...
SLACK_BOT_TOKEN=...
SLACK_APP_TOKEN=...
```

## Google Credentials (Optional)

Google integrations (Gmail, Calendar, Drive, etc.) require OAuth credentials. The `docker-compose.yml` mounts `google_credentials.json` and `google_token.json` from the project root into the container.

### Local Docker

Run `python3 setup.py` on your host machine before starting Docker. The setup wizard handles the Google OAuth browser flow and creates both files in the project root. Docker picks them up automatically via the volume mounts.

### Cloud / Remote Server

1. Run `python3 setup.py` on a machine with a browser to create `google_credentials.json` and `google_token.json`
2. Copy both files to the project root on your server:
   ```bash
   scp google_credentials.json google_token.json yourserver:~/noclaw/
   ```
3. Start Docker — the credentials are mounted read-only into the container

Alternatively, run `python3 setup.py` directly on the server and choose the headless OAuth option when prompted. This gives you a URL to open in any browser; after authorizing, you paste the redirect URL back into the terminal.

**Note:** If you haven't set up Google OAuth, the credential files won't exist. Docker will create empty directories in their place, which is harmless — Google integrations simply won't be available.

## Production Checklist

1. **Set `NOCLAW_API_KEY`** — protect webhook endpoints
2. **Mount data volume** — `./data:/app/data` for database persistence
3. **Mount workspace volume** — `./workspace:/app/workspace` for agent workspace
4. **Set up Google credentials** — if using Gmail, Calendar, or Drive integrations (see above)
5. **Configure log rotation** — via Docker logging driver
6. **Set up reverse proxy** — nginx or Caddy with TLS for external access
7. **Restrict channel users** — `TELEGRAM_USER_ID`, `SLACK_USER_ID`

## Reverse Proxy (nginx with TLS)

```nginx
server {
    listen 443 ssl http2;
    server_name assistant.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support (for dashboard)
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
    }
}
```

## Monitoring

- **Health:** `curl http://localhost:3000/health`
- **Dashboard:** `http://localhost:3000/dashboard`
- **Logs:** `docker-compose logs -f`
- **Agent performance:** `cat data/agents.jsonl | jq .`

## Backup

```bash
# Database
sqlite3 data/assistant.db ".backup data/assistant.db.backup"

# Workspace
tar -czf workspace-backup.tar.gz workspace/
```

## Updates

```bash
git pull origin main
docker-compose build
docker-compose up -d
curl http://localhost:3000/health
```
