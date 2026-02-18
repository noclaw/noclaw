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
    └── data/ (mounted volume)
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
- agentpool dependency
- Claude Code CLI (via Node.js)
- Non-root user

```dockerfile
FROM python:3.11-slim

# Install Node.js (required for Claude Code CLI)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user
RUN useradd -m -s /bin/bash noclaw

WORKDIR /app

# Install Python dependencies
COPY server/requirements.txt /app/server/
RUN pip install --no-cache-dir -r server/requirements.txt

# Copy application code
COPY server/ /app/server/
COPY run_assistant.py /app/

# Create data directory
RUN mkdir -p /app/data && chown -R noclaw:noclaw /app

USER noclaw

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

CMD ["python", "run_assistant.py"]
```

### docker-compose.yml

The [docker-compose.yml](../docker-compose.yml) provides:
- Data persistence via volume mount
- Health checks with auto-restart
- Log rotation (10MB, 3 files)
- Port mapping (default 3000)
- Environment from `.env` file

**Key:** No Docker socket mount is needed. The container uses `LocalSandbox` — shell commands run directly inside the container, which is already isolated.

```yaml
version: '3.8'

services:
  noclaw:
    build:
      context: .
      dockerfile: Dockerfile.server
    volumes:
      - ./data:/app/data
    env_file:
      - .env
    environment:
      - SANDBOX_TYPE=local
    ports:
      - "${PORT:-3000}:3000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

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
NOCLAW_API_KEY=secret        # Webhook authentication
SANDBOX_TYPE=local           # local or docker

# Channel plugins
TELEGRAM_BOT_TOKEN=...
TELEGRAM_USER_ID=...
SLACK_BOT_TOKEN=...
SLACK_APP_TOKEN=...
```

## Production Checklist

1. **Set `NOCLAW_API_KEY`** — protect webhook endpoints
2. **Set `SANDBOX_TYPE=local`** — the container itself provides isolation
3. **Mount data volume** — `./data:/app/data` for database and workspace persistence
4. **Configure log rotation** — via Docker logging driver
5. **Set up reverse proxy** — nginx or Caddy with TLS for external access
6. **Restrict channel users** — `TELEGRAM_USER_ID`, `SLACK_USER_ID`

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

# Workspaces
tar -czf workspaces-backup.tar.gz data/workspaces/
```

## Updates

```bash
git pull origin main
docker-compose build
docker-compose up -d
curl http://localhost:3000/health
```
