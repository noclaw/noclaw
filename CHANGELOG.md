# Changelog

## v0.3 - AgentPool Integration (2026-02-18)

### Major Changes
- **AgentPool integration** — Claude SDK now runs via [agentpool](https://github.com/noclaw/agentpool) instead of custom container orchestration
- **Channel plugins** — Telegram and Slack are auto-discovered from `server/channels/` and start when env vars are set
- **Simplified deployment** — Single process (FastAPI + agentpool), no separate worker containers

### Added
- `server/channels/` — Plugin system with auto-discovery (`base.py`, `__init__.py`)
- `server/channels/telegram_bot.py` — Built-in Telegram channel
- `server/channels/slack_bot.py` — Built-in Slack channel
- `docs/PLUGINS.md` — Channel plugin architecture documentation

### Removed
- `worker/` directory — No longer needed (agentpool handles SDK execution)
- `server/container_runner.py` — Replaced by agentpool sandboxing
- `build_worker.sh` — No worker image to build

### Changed
- `server/assistant.py` — Uses agentpool `run_session()`, channel lifecycle management
- `run_assistant.py` — Simplified startup, no `--docker`/`--local` flags
- `Dockerfile.server` — Installs Node.js + Claude Code CLI, no Docker-in-Docker
- `docker-compose.yml` — No Docker socket mount, uses `SANDBOX_TYPE=local`
- `.env.example` — Updated env vars (removed `WORKER_IMAGE`/`CONTAINER_*`, added `SANDBOX_TYPE`/`AGENT_TIMEOUT`/channels)
- `server/startup.py` — Docker is optional, checks for agentpool instead of worker image
- `setup.sh` — Checks for agentpool, Docker optional
- Skills (`/add-telegram`, `/add-slack`) — Rewritten as setup wizards (channels are now built-in)

### Documentation
- All docs updated for agentpool architecture
- `docs/ARCHITECTURE.md` — Rewritten for single-process model
- `docs/SECURITY.md` — Workspace isolation + optional Docker sandboxing
- `docs/LOGGING.md` — Application logs + agent performance logs
- `docs/DEPLOY.md` — Containerize host with LocalSandbox
- `QUICKSTART.md` — agentpool install steps, channel setup
- `CLAUDE.md`, `README.md` — Updated for v0.3

### Tests
- All 20 unit tests pass
- Fixed `test_env.py`, `test_cron_skill.py`, `run_tests.sh`, `test_docker.sh` for new architecture
