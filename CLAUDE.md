# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/ -v --tb=short

# Run a single test file
uv run pytest tests/test_scheduler.py -v

# Run a single test
uv run pytest tests/test_scheduler.py::test_pause_resume_cron -v

# Start the server locally (requires DATA_DIR)
DATA_DIR=/tmp/test-data uv run uvicorn app.main:app --port 8000

# Build Docker image
docker build -t scriptflow .

# Run in Docker
docker run -d -p 8000:8000 --name runner scriptflow
```

## Architecture

```
app/
  main.py           # FastAPI app, lifespan (startup recovery, Telegram bot)
  models.py         # SQLAlchemy models: Repo, Job, EnvVar, AppSettings
  database.py       # SQLite setup via SQLAlchemy
  scheduler.py      # APScheduler cron job management
  process_manager.py # asyncio process manager for "forever" mode jobs
  uv_manager.py     # Virtual environment creation and pip install
  github.py         # GitHub repo cloning/pulling
  notifications.py  # Apprise notifications
  log_utils.py      # Log file writing and rotation
  telegram_bot.py   # Telegram bot for remote job control
  routers/          # FastAPI routers: jobs, repos, logs, settings, wizard, validate, pages
  schemas.py        # Pydantic request/response schemas
  static/           # Web UI assets
```

### Job Execution Models

**"forever" mode**: ProcessManager (asyncio subprocess) runs the job continuously. On crash, auto-restarts with crash-loop detection (5 crashes in 60s → "crash-loop" status, no more auto-restart).

**"cron" mode**: APScheduler with SQLAlchemy job store. Cron expression stored in DB, jobs run on schedule.

### Data Storage

- **SQLite**: `{DATA_DIR}/db.sqlite` — tables: repos, jobs, env_vars, app_settings
- **Virtual envs**: `{DATA_DIR}/venvs/{job_id}/`
- **Logs**: `{DATA_DIR}/logs/{job_id}/stdout.log`, stderr.log
- **Repos**: `{DATA_DIR}/repos/{repo_id}/`

### Startup Recovery

On app start, the lifespan handler recovers "forever" jobs that were running before restart. Jobs marked `run_mode=forever` with `restart_on_crash=True` are restarted via ProcessManager.

### Telegram Bot

Enabled via `TELEGRAM_BOT_TOKEN` env var. Uses `python-telegram-bot` v20. Allows remote start/stop/restart of jobs.

## CI/CD

**GitHub Actions** (`.github/workflows/ci.yml`) — three sequential jobs:

| Trigger | `test` | `build-push` (GHCR) | `release` |
|---|---|---|---|
| PR opened | runs | skipped | skipped |
| Push to `main` | runs | runs (`latest` + `sha-*` tags) | skipped |
| `git tag vX.Y.Z && git push origin vX.Y.Z` | runs | runs (`vX.Y.Z` + `X.Y` tags) | runs (GitHub Release) |

**Image:** `ghcr.io/kushpvo/scriptflow:latest`

**To cut a release:**
```bash
git tag v1.0.0
git push origin v1.0.0
```

**Note:** GHCR packages are private by default on first push. Set visibility to Public at `github.com/kushpvo/scriptflow/pkgs/container/scriptflow` → Package settings.

## Design Docs

Design specifications are in `docs/superpowers/specs/`. These document feature intent before implementation.