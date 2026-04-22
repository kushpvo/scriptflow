import asyncio
import logging
import os
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from app.log_utils import write_log_line
from app.notifications import send_notification

DATA_DIR = os.environ.get("DATA_DIR", "/data")
logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        db_url = f"sqlite:///{DATA_DIR}/db.sqlite"
        jobstores = {"default": SQLAlchemyJobStore(url=db_url)}
        _scheduler = AsyncIOScheduler(jobstores=jobstores)
    return _scheduler


async def _run_cron_job(job_id: int, cmd: list[str], env: dict,
                        notification_url: str | None) -> None:
    start = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *cmd, env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    duration = time.monotonic() - start

    for line in stdout.decode(errors="replace").splitlines():
        write_log_line(job_id, "stdout", line)
    for line in stderr.decode(errors="replace").splitlines():
        write_log_line(job_id, "stderr", line)

    write_log_line(job_id, "stdout",
                   f"[runner] Cron run finished: exit={proc.returncode} duration={duration:.1f}s")

    if proc.returncode != 0 and notification_url:
        await send_notification(
            notification_url,
            f"Cron job {job_id} failed",
            f"Exit code {proc.returncode}",
        )


def add_cron_job(job_id: int, cron_expression: str, cmd: list[str],
                 env: dict, notification_url: str | None) -> None:
    fields = cron_expression.strip().split()
    if len(fields) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expression}")
    minute, hour, day, month, day_of_week = fields
    sched = get_scheduler()
    sched.add_job(
        _run_cron_job,
        "cron",
        id=f"job_{job_id}",
        replace_existing=True,
        kwargs={"job_id": job_id, "cmd": cmd, "env": env, "notification_url": notification_url},
        minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week,
    )


def remove_cron_job(job_id: int) -> None:
    sched = get_scheduler()
    job_key = f"job_{job_id}"
    if sched.get_job(job_key):
        sched.remove_job(job_key)


def pause_cron_job(job_id: int) -> None:
    get_scheduler().pause_job(f"job_{job_id}")


def resume_cron_job(job_id: int) -> None:
    get_scheduler().resume_job(f"job_{job_id}")