# ScriptFlow

A FastAPI-based job scheduler and process manager, supporting both continuous ("forever") and cron-based job execution with GitHub repo integration. Runs on any Docker host.

## Features

- **Job execution**: Run Python scripts as continuous processes or on a cron schedule
- **GitHub integration**: Clone and auto-pull repos for job entrypoints
- **Virtual environments**: Per-job `uv` virtual environments with auto-installed requirements
- **Crash recovery**: Auto-restart crashed "forever" jobs (with crash-loop detection)
- **Notifications**: Apprise-based notifications on job failure
- **Telegram bot**: Remote start/stop/restart via Telegram
- **Web UI**: Built-in dashboard for managing repos, jobs, and logs

## Quick Start

```bash
# Run with Docker
docker build -t scriptflow .
docker run -d -p 8000:8000 -v scriptflow-data:/data --name scriptflow scriptflow

# Or run locally
uv sync --extra dev
DATA_DIR=/tmp/run-data uv run uvicorn app.main:app --port 8000
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `/data` | Base directory for SQLite DB, venvs, logs, and repos |
| `TELEGRAM_BOT_TOKEN` | — | Enable Telegram bot for remote control |

## Job Run Modes

- **forever**: Runs continuously, auto-restarts on crash (5 crashes in 60s triggers "crash-loop" status, no more restarts)
- **cron**: Runs on a 5-field cron schedule (minute, hour, day, month, day-of-week)

## API

- `GET /api/jobs` — list all jobs
- `POST /api/jobs` — create job
- `POST /api/jobs/{id}/start` — start job
- `POST /api/jobs/{id}/stop` — stop job
- `PUT /api/jobs/{id}` — update job
- `DELETE /api/jobs/{id}` — delete job
- `POST /api/jobs/{id}/restart` — restart (forever mode only)

Web UI available at `/`.

## Development

```bash
uv sync --extra dev
uv run pytest tests/ -v --tb=short
DATA_DIR=/tmp/test-data uv run uvicorn app.main:app --port 8000
```