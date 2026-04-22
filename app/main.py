import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import app.database as db_mod
from app.log_utils import rotate_logs
from app.models import AppSettings, Job
from app.routers import jobs as jobs_router, logs, pages, repos, settings as settings_router, validate as validate_router, wizard
from app.routers.jobs import process_manager
from app.uv_manager import venv_python
from app.telegram_bot import run_telegram_bot

logger = logging.getLogger(__name__)


async def _nightly_rotation():
    while True:
        await asyncio.sleep(86400)  # 24h
        db = db_mod.SessionLocal()
        try:
            s = db.get(AppSettings, 1)
            days = s.log_retention_days if s else 30
        finally:
            db.close()
        rotate_logs(days)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_mod.init_db()

    # Startup recovery: restart jobs that were running
    db = db_mod.SessionLocal()
    try:
        running_jobs = db.query(Job).filter_by(status="running", run_mode="forever").all()
        for job in running_jobs:
            if job.restart_on_crash:
                logger.info(f"Recovering job {job.id}: {job.name}")
                # Build cmd and env
                DATA_DIR = os.environ.get("DATA_DIR", "/data")
                python = str(venv_python(job.id))
                entrypoint = os.path.join(DATA_DIR, "repos", str(job.repo_id), job.entrypoint)
                cmd = [python, entrypoint]
                if job.extra_args:
                    cmd += job.extra_args.split()
                env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
                for ev in job.env_vars:
                    env[ev.key] = ev.value
                try:
                    await process_manager.start(
                        job.id, cmd, env,
                        job.restart_on_crash, job.notification_url, job.notify_on_stderr,
                    )
                except Exception as e:
                    logger.error(f"Failed to recover job {job.id} ({job.name}): {e}")
                    job.status = "stopped"
                    db.commit()
            else:
                job.status = "stopped"
                db.commit()
                logger.info(f"Job {job.id} ({job.name}) restart disabled — marked stopped")
    finally:
        db.close()

    # Start nightly log rotation background task
    rotation_task = asyncio.create_task(_nightly_rotation())

    # Start optional Telegram bot
    bot_task = None
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        bot_task = asyncio.create_task(run_telegram_bot())

    yield

    rotation_task.cancel()
    try:
        await rotation_task
    except asyncio.CancelledError:
        pass

    if bot_task:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="ScriptFlow", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages.router)
app.include_router(repos.router)
app.include_router(jobs_router.router)
app.include_router(settings_router.router)
app.include_router(logs.router)
app.include_router(wizard.router)
app.include_router(validate_router.router)
