# Changelog

## v0.3.2 - Consolidated Setup (2026-02-23)

### Added
- **`setup.py`** — Interactive setup script (stdlib only) consolidating all setup into one place: prerequisites, agentpool, dependencies, `.env` configuration, Telegram, Slack, Google OAuth, and workspace scripts
- **Google OAuth in setup.py** — Step 7 walks through Google Cloud Console setup and runs the OAuth flow directly (browser or headless), replacing the separate `setup_auth.py`
- **Workspace script installation** — `setup.py` automatically runs `uv sync` in `workspace/.claude/scripts/` to install integration dependencies
- **`TIMEZONE` env var** — Used by Gmail and Google Calendar integrations (default: `America/Denver`)
- **Acknowledgement** — Credited Cole Medin and [Dynamous](https://dynamous.ai/) for Google integration agent skills

### Changed
- **Google credential paths** — `google_credentials.json` and `google_token.json` now stored in project root (auto-migrated from old `workspace/.claude/scripts/integrations/` location)
- **`workspace/.claude/scripts/config.py`** — Credential paths point to project root
- **`workspace/.claude/scripts/integrations/registry.py`** — Uses config import instead of hardcoded path
- **`workspace/.claude/scripts/pyproject.toml`** — Renamed to `noclaw-scripts`, trimmed unused dependencies (kept: `python-dotenv`, `google-api-python-client`, `google-auth-oauthlib`, `slack-sdk`)
- **`setup.sh`** — Now a thin wrapper that calls `setup.py`
- **`server/requirements.txt`** — Removed hardcoded agentpool local path (setup.py handles installation)
- **`.env.example`** — Added `TIMEZONE`, updated Google section, channel setup references `setup.py`
- **`.gitignore`** — Root-level `google_credentials.json` and `google_token.json`

### Removed
- **`setup_agentpool.py`** — Functionality moved into `setup.py` step 2
- **`.claude/skills/add-telegram/`** — Telegram setup moved into `setup.py` step 5
- **`.claude/skills/add-slack/`** — Slack setup moved into `setup.py` step 6
- **`workspace/.claude/scripts/setup_auth.py`** — Google OAuth moved into `setup.py` step 7

### Documentation
- All docs updated for consolidated setup and removed skills
- `QUICKSTART.md` — Primary path is `python3 setup.py`
- `CLAUDE.md` — Removed add-telegram/add-slack skills, updated agent skills section
- `README.md` — Updated quick start, added Dynamous acknowledgement

## v0.3.1 - Shared Workspace + Remove SANDBOX_TYPE (2026-02-21)

### Changed
- **Single shared workspace** — Replaced per-user `data/workspaces/{user_id}/` with a single `workspace/` directory at project root
- **Workspace has its own `.claude/`** — Agent skills in `workspace/.claude/skills/` are separate from developer skills in `.claude/skills/`
- **Removed SANDBOX_TYPE** — No longer a config option; production isolation achieved by running NoClaw in a Docker container
- `server/assistant.py` — Uses shared `WORKSPACE_DIR`, removed `SandboxType` import and `sandbox` webhook parameter
- `server/context_manager.py` — Accepts `workspace_dir` parameter, all users share the same workspace
- `server/security.py` — Validates against shared workspace root
- `server/heartbeat.py` — Simplified default checklist (no user_id in header)
- `server/startup.py` — Removed Docker/Podman runtime check
- `docker-compose.yml` — Added `workspace` volume mount, removed `SANDBOX_TYPE` env
- `Dockerfile.server` — Creates `/app/workspace` directory
- All documentation updated for shared workspace and simplified security model
- All tests updated and passing

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
