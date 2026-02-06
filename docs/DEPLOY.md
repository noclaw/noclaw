# NoClaw Deployment Guide

This guide covers deploying NoClaw to production environments.

## Deployment Architecture

NoClaw has two container layers:

1. **Server Container** (optional) - The FastAPI server itself
   - Built with `Dockerfile.server`
   - Deployed with `docker-compose.yml`
   - Persistent: runs continuously

2. **Worker Containers** (required) - Claude SDK execution
   - Built with `worker/Dockerfile`
   - Spawned per request by the server
   - Ephemeral: created and destroyed per request

## Deployment Options

### Option 1: Native Python + Worker Containers (Recommended for Development)

Run the FastAPI server directly on the host, spawn worker containers as needed.

**Pros:**
- Fast iteration during development
- Easy to debug server code
- Direct access to logs

**Setup:**
```bash
# Install dependencies
pip3 install -r server/requirements.txt

# Build worker container
./build_worker.sh

# Run server
python run_assistant.py
```

**Architecture:**
```
Host Machine
├── Python FastAPI server (native)
│   └── Spawns worker containers → Docker
└── Docker daemon
    └── Worker containers (ephemeral)
```

---

### Option 2: Full Docker Deployment (Recommended for Production)

Run both server and workers in containers using docker-compose.

**Pros:**
- Complete isolation
- Easy deployment to cloud/VPS
- Consistent environment
- Log management
- Auto-restart policies

**Setup:**

1. **Configure environment:**
```bash
# Create .env file
cp .env.example .env
nano .env
```

Add your credentials:
```env
CLAUDE_CODE_OAUTH_TOKEN=your-token-here
PORT=3000
DATA_DIR=/app/data
LOG_LEVEL=INFO
```

2. **Build and run:**
```bash
# Build server image and worker image
docker-compose build

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

**Architecture:**
```
Docker Host
└── docker-compose
    ├── noclaw-assistant (server container)
    │   ├── FastAPI server
    │   ├── Docker CLI (for spawning workers)
    │   └── Mounts: /var/run/docker.sock
    └── Worker containers (spawned by server)
        └── Claude SDK execution
```

---

## Docker Compose Configuration

The [docker-compose.yml](../docker-compose.yml) provides:

### Features
- **Container-in-container** - Server spawns worker containers via Docker socket
- **Data persistence** - `./data` mounted for SQLite database
- **Workspace persistence** - User workspaces mounted
- **Health checks** - Automatic health monitoring
- **Auto-restart** - Restarts on failure
- **Log rotation** - 10MB max, 3 files retained
- **Port mapping** - Exposes configured port (default 3000)

### Volumes
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock  # Docker socket for spawning workers
  - ./data:/app/data                           # Database persistence
  - ${WORKSPACE_ROOT:-./workspaces}:/workspaces # User workspaces
```

### Environment
Loads from `.env` file:
- `CLAUDE_CODE_OAUTH_TOKEN` - Claude authentication (required)
- `PORT` - Server port (default: 3000)
- `DATA_DIR` - Data directory (default: /app/data)
- `LOG_LEVEL` - Logging level (default: INFO)
- `WORKSPACE_ROOT` - User workspaces location

---

## Production Deployment

### Prerequisites
- Docker Engine 20.10+
- Docker Compose v2+
- 2GB+ RAM (1GB for server, 1GB+ for worker containers)
- 10GB+ disk space

### Security Considerations

1. **Docker Socket Access**
   - Server needs `/var/run/docker.sock` to spawn workers
   - This grants Docker API access (required for container-in-container)
   - Run on trusted host or use rootless Docker

2. **Network Isolation**
   - Worker containers need internet access for Claude API
   - Server exposes port 3000 (configure firewall as needed)
   - Consider using reverse proxy (nginx, Caddy) with TLS

3. **Secrets Management**
   - Never commit `.env` to version control
   - Use Docker secrets in production:
     ```yaml
     secrets:
       claude_token:
         external: true
     ```
   - Or use environment injection from orchestrator

4. **API Key Protection**
   - Set `NOCLAW_API_KEY` in `.env` for webhook authentication
   - Requires `X-API-Key` header on all requests
   - Prevents unauthorized access to your assistant

### Cloud Deployment Examples

#### Deploy to VPS (DigitalOcean, Linode, etc.)

```bash
# SSH to your server
ssh user@your-server.com

# Clone repository
git clone https://github.com/your-org/noclaw.git
cd noclaw

# Configure environment
cp .env.example .env
nano .env  # Add your credentials

# Build and start
docker-compose up -d

# Configure firewall (example for ufw)
sudo ufw allow 3000/tcp

# Optional: Setup reverse proxy
# See nginx example below
```

#### Nginx Reverse Proxy (with TLS)

```nginx
# /etc/nginx/sites-available/noclaw
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

        # WebSocket support (for dashboard SSE)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Monitoring

### Health Checks

The server exposes a health endpoint:
```bash
curl http://localhost:3000/health
```

Returns:
```json
{
  "status": "healthy",
  "version": "0.2.0"
}
```

### Dashboard

Access the monitoring dashboard:
```
http://localhost:3000/dashboard
```

Shows:
- Active users
- Container status
- System resources
- Recent logs
- Heartbeat status

### Logs

**Docker Compose logs:**
```bash
# Follow logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service
docker-compose logs -f noclaw
```

**Structured logging:**
- Default format: Human-readable with colors
- JSON format: Set `LOG_FORMAT=json` in `.env`
- Log file: Set `LOG_FILE=/app/data/noclaw.log` in `.env`

---

## Maintenance

### Backup

**Database:**
```bash
# Backup SQLite database
cp ./data/assistant.db ./data/assistant.db.backup

# Or use SQLite backup
sqlite3 ./data/assistant.db ".backup ./data/assistant.db.backup"
```

**User workspaces:**
```bash
# Tar backup
tar -czf workspaces-backup.tar.gz ./data/workspaces/

# Rsync to remote
rsync -av ./data/workspaces/ user@backup-server:/backups/noclaw/
```

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild containers
docker-compose build

# Restart with new version
docker-compose up -d

# Check health
curl http://localhost:3000/health
```

### Cleanup

**Remove old worker containers:**
```bash
# Worker containers are ephemeral and auto-removed
# But if cleanup fails, manually remove:
docker container prune -f
```

**Remove old images:**
```bash
# Remove unused images
docker image prune -a
```

**Logs:**
```bash
# Clear Docker logs
truncate -s 0 $(docker inspect --format='{{.LogPath}}' noclaw-assistant)
```

---

## Troubleshooting

### Server won't start

**Check logs:**
```bash
docker-compose logs noclaw
```

**Common issues:**
- Missing `CLAUDE_CODE_OAUTH_TOKEN` in `.env`
- Port 3000 already in use (change `PORT` in `.env`)
- Docker socket not accessible

### Worker containers fail

**Check worker image:**
```bash
docker images | grep noclaw-worker
```

**Rebuild worker:**
```bash
./build_worker.sh
```

**Memory issues:**
- Worker containers need 1GB+ memory
- Set `CONTAINER_MEMORY_LIMIT=1g` in `.env`

### Health check failing

**Test directly:**
```bash
docker exec noclaw-assistant curl http://localhost:3000/health
```

**Check server is running:**
```bash
docker exec noclaw-assistant ps aux | grep python
```

### Can't spawn workers

**Check Docker socket:**
```bash
docker exec noclaw-assistant docker ps
```

If this fails, Docker socket isn't mounted correctly.

**Verify volume mount:**
```bash
docker inspect noclaw-assistant | grep docker.sock
```

---

## Performance Tuning

### Resource Limits

**Server container** (Dockerfile.server):
- No explicit limits (adjust in docker-compose.yml if needed)
- Typically uses 200-500MB RAM

**Worker containers** (built by build_worker.sh):
- Default: 1GB RAM limit
- Adjust in `.env`: `CONTAINER_MEMORY_LIMIT=2g`
- CPU limit: Adjust in `container_runner.py`

### Concurrent Requests

The server handles requests sequentially by default. For concurrent requests:
- Use multiple server instances behind a load balancer
- Each server can spawn its own worker containers
- Share database via network mount or PostgreSQL

---

## Scaling

### Horizontal Scaling

Run multiple NoClaw instances behind nginx:

```nginx
upstream noclaw_backend {
    server noclaw-1:3000;
    server noclaw-2:3000;
    server noclaw-3:3000;
}

server {
    location / {
        proxy_pass http://noclaw_backend;
    }
}
```

**Note:** All instances should share the same database and workspaces via network storage.

### Database Scaling

For high load, migrate from SQLite to PostgreSQL:
1. Update `context_manager.py` to use PostgreSQL
2. Update connection strings in `.env`
3. Use managed PostgreSQL (AWS RDS, DigitalOcean, etc.)

---

## Summary

**For Development:**
```bash
./setup.sh
python run_assistant.py
```

**For Production:**
```bash
cp .env.example .env
# Add CLAUDE_CODE_OAUTH_TOKEN
docker-compose up -d
```

**Monitor:**
- Health: `curl http://localhost:3000/health`
- Dashboard: `http://localhost:3000/dashboard`
- Logs: `docker-compose logs -f`

---

*This deployment guide covers production-ready NoClaw deployments. For basic setup, see [QUICKSTART.md](../QUICKSTART.md).*
