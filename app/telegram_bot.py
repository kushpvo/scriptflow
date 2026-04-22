import asyncio
import logging
import os
import time as _time

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

import app.database as db_mod
from app.models import Job
from app.routers.jobs import _build_cmd, _build_env, process_manager
from app.scheduler import pause_cron_job, resume_cron_job
from app.log_utils import write_log_line

logger = logging.getLogger(__name__)

_ALLOWED_USERS: set[int] = set()

STATUS_EMOJI: dict[str, str] = {
    "running":        "✅",
    "idle":           "💤",
    "paused":         "⏸",
    "stopped":        "⛔",
    "crashed":        "💥",
    "crash-loop":     "🔁",
    "install_failed": "⚠️",
}

HELP_TEXT = (
    "🤖 *ScriptFlow Bot*\n\n"
    "/list — list all jobs with status\n"
    "/info <id> — show job details\n"
    "/pause <id> — pause a job\n"
    "/resume <id> — resume a paused job\n"
    "/restart <id> — restart a forever job\n"
    "/run <id> — run a cron job once immediately\n"
    "/help — show this message"
)


def _allowed(update: Update) -> bool:
    return update.effective_user.id in _ALLOWED_USERS


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    db = db_mod.SessionLocal()
    try:
        jobs = db.query(Job).all()
    finally:
        db.close()
    if not jobs:
        await update.message.reply_text("No jobs configured.")
        return
    lines = ["📋 *Jobs*\n"]
    for job in jobs:
        status = process_manager.get_status(job.id) if job.run_mode == "forever" else job.status
        emoji = STATUS_EMOJI.get(status, "❓")
        lines.append(f"`{job.id}` · {job.name}   {job.run_mode}   {emoji} {status}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


_CRON_READABLE: dict[str, str] = {
    "* * * * *":  "Every minute",
    "0 * * * *":  "Every hour",
    "0 0 * * *":  "Every day at midnight",
    "0 9 * * *":  "Every day at 9:00 AM",
    "0 12 * * *": "Every day at noon",
    "0 0 1 * *":  "First day of each month",
    "0 0 * * 0":  "Every Sunday at midnight",
}


def _cron_label(expr: str) -> str:
    return _CRON_READABLE.get(expr.strip(), expr)


async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /info <id>")
        return
    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Job ID must be an integer.")
        return
    db = db_mod.SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            await update.message.reply_text(f"❌ Job {job_id} not found")
            return
        status = process_manager.get_status(job.id) if job.run_mode == "forever" else job.status
        emoji = STATUS_EMOJI.get(status, "❓")
        mode_line = job.run_mode
        if job.run_mode == "cron" and job.cron_expression:
            mode_line = f"cron · `{job.cron_expression}` ({_cron_label(job.cron_expression)})"
        restart_line = f"\nRestart:   {'yes' if job.restart_on_crash else 'no'}" if job.run_mode == "forever" else ""
        text = (
            f"ℹ️ *{job.name}*\n\n"
            f"Status:    {emoji} {status}\n"
            f"Mode:      {mode_line}\n"
            f"Repo:      {job.repo.github_url}\n"
            f"Entry:     `{job.entrypoint}`\n"
            f"Python:    {job.python_version}\n"
            f"Auto-pull: {'yes' if job.auto_pull else 'no'}"
            f"{restart_line}"
        )
    finally:
        db.close()
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /pause <id>")
        return
    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Job ID must be an integer.")
        return
    db = db_mod.SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            await update.message.reply_text(f"❌ Job {job_id} not found")
            return
        if job.run_mode == "forever":
            current = process_manager.get_status(job_id)
            if current != "running":
                await update.message.reply_text(f"Job is already {current}")
                return
            await process_manager.stop(job_id)
            job.status = "stopped"
        else:
            if job.status == "paused":
                await update.message.reply_text("Job is already paused")
                return
            pause_cron_job(job_id)
            job.status = "paused"
        db.commit()
        name = job.name
    finally:
        db.close()
    await update.message.reply_text(f"⏸ Paused: {name}")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /resume <id>")
        return
    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Job ID must be an integer.")
        return
    db = db_mod.SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            await update.message.reply_text(f"❌ Job {job_id} not found")
            return
        if job.run_mode == "forever":
            current = process_manager.get_status(job_id)
            if current == "running":
                await update.message.reply_text("Job is already running")
                return
            cmd = _build_cmd(job)
            env = _build_env(job)
            await process_manager.start(
                job_id, cmd, env,
                job.restart_on_crash, job.notification_url, job.notify_on_stderr,
            )
            job.status = "running"
        else:
            if job.status != "paused":
                await update.message.reply_text(f"Job is not paused (status: {job.status})")
                return
            resume_cron_job(job_id)
            job.status = "idle"
        db.commit()
        name = job.name
    finally:
        db.close()
    await update.message.reply_text(f"▶️ Resumed: {name}")


async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /restart <id>")
        return
    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Job ID must be an integer.")
        return
    db = db_mod.SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            await update.message.reply_text(f"❌ Job {job_id} not found")
            return
        if job.run_mode != "forever":
            await update.message.reply_text("❌ /restart only works on forever jobs")
            return
        name = job.name
        current = process_manager.get_status(job_id)
        was_running = current == "running"
        if was_running:
            await process_manager.stop(job_id)
        cmd = _build_cmd(job)
        env = _build_env(job)
        await process_manager.start(
            job_id, cmd, env,
            job.restart_on_crash, job.notification_url, job.notify_on_stderr,
        )
        job.status = "running"
        db.commit()
    finally:
        db.close()
    if was_running:
        await update.message.reply_text(f"🔄 Restarting: {name} (was running)")
    else:
        await update.message.reply_text(f"🔄 Restarted: {name}")


async def _run_once_and_notify(
    job_id: int, name: str, cmd: list[str], env: dict,
    chat_id: int, bot,
) -> None:
    start = _time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *cmd, env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    elapsed = _time.monotonic() - start
    for line in stdout.decode(errors="replace").splitlines():
        write_log_line(job_id, "stdout", line)
    for line in stderr.decode(errors="replace").splitlines():
        write_log_line(job_id, "stderr", line)
    if proc.returncode == 0:
        msg = f"✅ {name} finished (exit 0, {elapsed:.1f}s)"
    else:
        msg = f"❌ {name} failed (exit {proc.returncode}, {elapsed:.1f}s)"
    await bot.send_message(chat_id=chat_id, text=msg)


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /run <id>")
        return
    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Job ID must be an integer.")
        return
    db = db_mod.SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            await update.message.reply_text(f"❌ Job {job_id} not found")
            return
        if job.run_mode != "cron":
            await update.message.reply_text("❌ /run only works on cron jobs")
            return
        cmd = _build_cmd(job)
        env = _build_env(job)
        name = job.name
    finally:
        db.close()
    await update.message.reply_text(f"▶️ Running {name}…")
    asyncio.create_task(_run_once_and_notify(
        job_id, name, cmd, env,
        update.effective_chat.id, context.bot,
    ))


async def run_telegram_bot() -> None:
    global _ALLOWED_USERS
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    raw = os.environ.get("TELEGRAM_ALLOWED_USERS", "")
    _ALLOWED_USERS = {int(x) for x in raw.split(",") if x.strip()}

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("list",   cmd_list))
    application.add_handler(CommandHandler("info",   cmd_info))
    application.add_handler(CommandHandler("pause",  cmd_pause))
    application.add_handler(CommandHandler("resume", cmd_resume))
    application.add_handler(CommandHandler("restart", cmd_restart))
    application.add_handler(CommandHandler("run",    cmd_run))
    application.add_handler(CommandHandler("help",   cmd_help))

    commands = [
        BotCommand("list",   "List all jobs with status"),
        BotCommand("info",   "Show job details (/info <id>)"),
        BotCommand("pause",  "Pause a job (/pause <id>)"),
        BotCommand("resume", "Resume a paused job (/resume <id>)"),
        BotCommand("restart", "Restart a forever job (/restart <id>)"),
        BotCommand("run",    "Run a cron job once (/run <id>)"),
        BotCommand("help",   "Show help"),
    ]

    async with application:
        await application.bot.set_my_commands(commands)
        await application.start()
        await application.updater.start_polling()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        finally:
            await application.updater.stop()
            await application.stop()