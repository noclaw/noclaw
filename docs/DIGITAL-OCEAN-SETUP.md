# Digital Ocean Setup Guide

Deploy NoClaw as a headless AI assistant on a Digital Ocean Droplet. This is for server-only deployment — no macOS desktop control features.

## Architecture

```
┌──────────────────────────────────────────────────┐
│ Digital Ocean Droplet (2GB RAM / 1 vCPU - $12/mo) │
├──────────────────────────────────────────────────┤
│                                                    │
│  Nginx (HTTPS reverse proxy)                       │
│    └─→ NoClaw FastAPI (port 3000)                  │
│                                                    │
│  Docker Compose:                                   │
│    └─→ noclaw (FastAPI + Claude Code CLI)           │
│                                                    │
│  Volumes:                                          │
│    ├─→ data/ (SQLite database, agent logs)          │
│    └─→ workspace/ (agent workspace, skills, tasks)  │
│                                                    │
└──────────────────────────────────────────────────┘
```

Channels (Telegram, Slack) connect directly to the NoClaw server. The `noclaw` CLI client connects over HTTPS.

## Prerequisites

- Digital Ocean account ([digitalocean.com](https://www.digitalocean.com))
- Domain name (optional but recommended for HTTPS)
- Claude.ai Pro or Max subscription
- OAuth token from `claude setup-token` (run on your local machine)

## Step 1: Create Droplet

Using the web console or CLI:

```bash
doctl compute droplet create noclaw \
  --image docker-20-04 \
  --size s-1vcpu-2gb \
  --region nyc1 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header)
```

**Specs:** 2GB RAM / 1 vCPU is sufficient for a single-user assistant. The "Docker on Ubuntu" marketplace image comes with Docker pre-installed. ~$12/month.

For heavier usage (parallel agents, long tasks), consider 4GB RAM ($24/month).

## Step 2: Initial Server Setup

```bash
ssh root@<DROPLET_IP>

# Update system
apt update && apt upgrade -y

# Clone repository
cd /opt
git clone https://github.com/noclaw/noclaw.git
cd noclaw
```

## Step 3: Configure Environment

```bash
cp .env.example .env
nano .env
```

Set these values:

```bash
# Required — get from 'claude setup-token' on your local machine
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here

# Server
PORT=3000

# Webhook security — generate with: openssl rand -hex 32
NOCLAW_API_KEY=your-secret-key-here

# Agent
AGENT_TIMEOUT=300

# Logging
LOG_LEVEL=INFO
AGENT_LOG_FILE=data/agents.jsonl
```

Optional channels (add if needed):

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_USER_ID=your-user-id
TELEGRAM_MODEL_HINT=sonnet

# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_USER_ID=U12345678
SLACK_MODEL_HINT=sonnet
```

## Step 4: Build and Start

```bash
# Create data and workspace directories
mkdir -p data workspace

# Build and start (entrypoint auto-fixes volume permissions)
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f
```

Verify it's running:

```bash
curl http://localhost:3000/health
```

## Step 5: Configure Firewall

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (for certbot)
ufw allow 443/tcp   # HTTPS
ufw --force enable
```

Do **not** expose port 3000 directly — Nginx will proxy to it.

## Step 6: Setup Nginx Reverse Proxy

```bash
apt install -y nginx

cat > /etc/nginx/sites-available/noclaw << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;  # Match AGENT_TIMEOUT
        proxy_connect_timeout 60s;
    }

    # Dashboard — restrict access (see options below)
    location /dashboard {
        # Option A: Allow specific IPs only (recommended)
        # allow 203.0.113.10;   # Your home IP
        # allow 10.0.0.0/8;     # VPN/private network
        # deny all;

        # Option B: Basic auth (see instructions below)
        # auth_basic "NoClaw Dashboard";
        # auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE for dashboard (inherits access rules from /dashboard)
    location /dashboard/stream {
        # Copy the same allow/deny or auth_basic rules from /dashboard above

        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }

    client_max_body_size 10M;
}
EOF

ln -s /etc/nginx/sites-available/noclaw /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
mkdir -p /var/www/html/.well-known/acme-challenge
nginx -t && systemctl restart nginx && systemctl enable nginx
```

**Important:** Replace `your-domain.com` with your actual domain. If you don't have a domain, you can use the Droplet IP directly (skip the SSL step).

### Restricting Dashboard Access

The dashboard has no built-in authentication. Choose one approach:

**Option A — IP allowlist** (simplest, good for static IPs):

Uncomment the `allow`/`deny` lines in both `/dashboard` and `/dashboard/stream` location blocks above, replacing with your IP.

Find your public IP: `curl ifconfig.me`

**Option B — Basic auth** (works with any IP):

```bash
apt install -y apache2-utils
htpasswd -c /etc/nginx/.htpasswd noclaw   # Set a password
```

Uncomment the `auth_basic` lines in both `/dashboard` and `/dashboard/stream` location blocks, then reload:

```bash
nginx -t && systemctl reload nginx
```

## Step 7: Setup SSL with Let's Encrypt

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
certbot renew --dry-run  # Test auto-renewal
```

If certbot fails, ensure:
- DNS A record points to your Droplet IP
- Firewall allows ports 80 and 443
- The `/.well-known/acme-challenge/` location block is in Nginx config

## Step 8: Configure the CLI Client

On your **local machine**, set up the `noclaw` CLI to talk to the Droplet.

```bash
mkdir -p ~/.local/bin
scp root@<DROPLET_IP>:/opt/noclaw/noclaw ~/.local/bin/noclaw
chmod +x ~/.local/bin/noclaw
```

Configure it:

```bash
cat > ~/.noclaw << 'EOF'
url=https://your-domain.com
api_key=your-secret-key-here
EOF
```

Test it:

```bash
noclaw health
noclaw send "Hello from my laptop"
noclaw reply "Thanks"
```

## Step 9: Verify

```bash
# From the Droplet
docker compose logs --tail 20

# From your local machine
noclaw health
noclaw send "What's the current date and time?"
noclaw status
noclaw dashboard  # Opens web dashboard
```

## Google OAuth Setup (Gmail, Calendar, Drive)

To use Google integrations (email, calendar, spreadsheets, etc.), you need to set up OAuth credentials and run the auth flow.

### 1. Get OAuth Credentials

On your local machine:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use existing)
3. Enable the APIs you need: Gmail, Calendar, Sheets, Docs, Drive
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Choose **Desktop app** as the application type
6. Download the credentials JSON file

### 2. Copy Credentials to Server

```bash
scp google_credentials.json root@<DROPLET_IP>:/opt/noclaw/workspace/google_credentials.json
```

### 3. Run Headless Auth Flow

The auth flow generates a URL you open in your local browser, then paste back the redirect URL.

```bash
ssh root@<DROPLET_IP>
cd /opt/noclaw

# Run auth inside the container interactively
docker compose exec noclaw python3 -c "
import sys
sys.path.insert(0, '/app/workspace/.claude/scripts')
from integrations.auth import run_initial_auth
run_initial_auth(headless=True)
"
```

This will:
1. Print an authorization URL — open it in your local browser
2. Authorize the app and grant permissions
3. Google redirects to `localhost:1` which fails — **that's expected**
4. Copy the full URL from your browser's address bar
5. Paste it back into the SSH terminal

The token is saved to `workspace/google_token.json` and auto-refreshes.

### 4. Verify

```bash
noclaw send "How many unread emails do I have?"
```

If the token expires and can't refresh, re-run step 3.

## Updating

```bash
ssh root@<DROPLET_IP>
cd /opt/noclaw
git pull
docker compose up -d --build
```

## Backup

The SQLite database and workspace are mounted as volumes. Back them up:

```bash
cat > /usr/local/bin/backup-noclaw.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/var/backups/noclaw"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

# Backup data and workspace
tar -czf $BACKUP_DIR/noclaw_${TIMESTAMP}.tar.gz \
  -C /opt/noclaw data/ workspace/

# Clean old backups
find $BACKUP_DIR -name "noclaw_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: noclaw_${TIMESTAMP}.tar.gz"
EOF

chmod +x /usr/local/bin/backup-noclaw.sh
```

Schedule daily backup:

```bash
# Add to crontab (crontab -e):
0 2 * * * /usr/local/bin/backup-noclaw.sh >> /var/log/noclaw-backup.log 2>&1
```

## Monitoring

```bash
# Container status
docker compose ps

# Live logs
docker compose logs -f

# Nginx logs
tail -f /var/log/nginx/error.log

# Disk space
df -h

# Docker disk usage
docker system df
```

## Cost

| Component | Monthly Cost |
|-----------|-------------|
| Droplet (2GB/1vCPU) | $12 |
| Droplet (4GB/2vCPU) | $24 |
| Let's Encrypt SSL | $0 |
| Domain (.com) | ~$1 |
| **Total** | **~$13-25** |

## Troubleshooting

### "Invalid bearer token" (401)
- The `CLAUDE_CODE_OAUTH_TOKEN` in `.env` is invalid or expired
- Make sure the token is on a **single line** — long tokens wrap when pasting
- Regenerate with `claude setup-token` on your local machine, then update `.env` and restart: `docker compose restart`

### Container keeps restarting
- Check logs: `docker compose logs --tail 50`
- Verify `.env` file exists and has `CLAUDE_CODE_OAUTH_TOKEN`
- Ensure the `data/` and `workspace/` directories exist: `mkdir -p data workspace`
  - The entrypoint script auto-fixes permissions, but you can also run: `chown -R 1000:1000 data workspace`

### Database errors
- Delete and let it recreate: `rm data/assistant.db && docker compose restart`

### Nginx 502 Bad Gateway
- The NoClaw container isn't running: `docker compose ps`
- Port mismatch: ensure Nginx proxies to `localhost:3000` and `.env` has `PORT=3000`

### Certbot ACME challenge fails
- Ensure firewall allows ports 80 and 443
- Verify DNS A record points to your Droplet IP
- Check Nginx has the `/.well-known/acme-challenge/` location block

### Agent timeout on long tasks
- Increase `AGENT_TIMEOUT` in `.env`
- Also increase `proxy_read_timeout` in Nginx config to match
- Restart both: `docker compose restart && systemctl restart nginx`

### Google OAuth "No valid token" or "refresh failed"
- Ensure `workspace/google_credentials.json` exists on the host
- Re-run the headless auth flow (see [Google OAuth Setup](#google-oauth-setup-gmail-calendar-drive))
- Check file permissions: `chown -R 1000:1000 workspace/`

### SSL certificate renewal
```bash
certbot renew --force-renewal
certbot certificates
```

## Maintenance

- **Daily:** Backups run automatically (if cron configured)
- **Weekly:** Clean Docker resources: `docker system prune -f`
- **Monthly:** Update system packages: `apt update && apt upgrade -y`
- **As needed:** Update NoClaw: `git pull && docker compose up -d --build`
