import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import app.telegram_bot as bot_mod


def _set_allowed(*user_ids):
    bot_mod._ALLOWED_USERS = set(user_ids)


def _make_update(user_id: int) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat.id = 999
    update.message.reply_text = AsyncMock()
    return update


def _make_context(args=None) -> MagicMock:
    ctx = MagicMock()
    ctx.args = args or []
    ctx.bot.send_message = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_unauthorized_user_is_silently_ignored():
    _set_allowed(111)
    update = _make_update(user_id=999)
    ctx = _make_context()
    await bot_mod.cmd_list(update, ctx)
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_list_no_jobs():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context()
    with patch("app.telegram_bot.db_mod") as mock_db:
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.all.return_value = []
        await bot_mod.cmd_list(update, ctx)
    update.message.reply_text.assert_called_once_with("No jobs configured.")


@pytest.mark.asyncio
async def test_list_shows_jobs():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context()
    job = MagicMock()
    job.id = 1
    job.name = "fetcher"
    job.run_mode = "forever"
    job.status = "running"
    with patch("app.telegram_bot.db_mod") as mock_db, \
         patch("app.telegram_bot.process_manager") as mock_pm:
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.query.return_value.all.return_value = [job]
        mock_pm.get_status.return_value = "running"
        await bot_mod.cmd_list(update, ctx)
    call_args = update.message.reply_text.call_args
    assert "fetcher" in call_args[0][0]
    assert "✅" in call_args[0][0]


@pytest.mark.asyncio
async def test_help_returns_text():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context()
    await bot_mod.cmd_help(update, ctx)
    update.message.reply_text.assert_called_once()
    assert "/list" in update.message.reply_text.call_args[0][0]


def test_status_emoji_covers_all_statuses():
    for status in ("running", "idle", "paused", "stopped", "crashed", "crash-loop", "install_failed"):
        assert status in bot_mod.STATUS_EMOJI


@pytest.mark.asyncio
async def test_pause_running_forever_job():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context(args=["1"])
    job = MagicMock()
    job.id = 1
    job.name = "fetcher"
    job.run_mode = "forever"
    job.status = "running"
    with patch("app.telegram_bot.db_mod") as mock_db, \
         patch("app.telegram_bot.process_manager") as mock_pm:
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = job
        mock_pm.get_status.return_value = "running"
        mock_pm.stop = AsyncMock()
        await bot_mod.cmd_pause(update, ctx)
        mock_pm.stop.assert_called_once_with(1)
    assert "⏸" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_pause_idle_cron_job():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context(args=["2"])
    job = MagicMock()
    job.id = 2
    job.name = "report"
    job.run_mode = "cron"
    job.status = "idle"
    with patch("app.telegram_bot.db_mod") as mock_db, \
         patch("app.telegram_bot.pause_cron_job") as mock_pause:
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = job
        await bot_mod.cmd_pause(update, ctx)
        mock_pause.assert_called_once_with(2)
    assert job.status == "paused"


@pytest.mark.asyncio
async def test_pause_already_paused_cron_job():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context(args=["2"])
    job = MagicMock()
    job.id = 2
    job.run_mode = "cron"
    job.status = "paused"
    with patch("app.telegram_bot.db_mod") as mock_db:
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = job
        await bot_mod.cmd_pause(update, ctx)
    assert "already paused" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_resume_stopped_forever_job():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context(args=["1"])
    job = MagicMock()
    job.id = 1
    job.name = "fetcher"
    job.run_mode = "forever"
    job.status = "stopped"
    job.restart_on_crash = True
    job.notification_url = None
    job.notify_on_stderr = False
    with patch("app.telegram_bot.db_mod") as mock_db, \
         patch("app.telegram_bot.process_manager") as mock_pm, \
         patch("app.telegram_bot._build_cmd", return_value=["python", "main.py"]), \
         patch("app.telegram_bot._build_env", return_value={}):
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = job
        mock_pm.get_status.return_value = "stopped"
        mock_pm.start = AsyncMock()
        await bot_mod.cmd_resume(update, ctx)
        mock_pm.start.assert_called_once()
    assert "▶️" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_resume_paused_cron_job():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context(args=["2"])
    job = MagicMock()
    job.id = 2
    job.name = "report"
    job.run_mode = "cron"
    job.status = "paused"
    with patch("app.telegram_bot.db_mod") as mock_db, \
         patch("app.telegram_bot.resume_cron_job") as mock_resume:
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = job
        await bot_mod.cmd_resume(update, ctx)
        mock_resume.assert_called_once_with(2)
    assert job.status == "idle"


@pytest.mark.asyncio
async def test_info_shows_job_details():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context(args=["1"])
    job = MagicMock()
    job.id = 1
    job.name = "fetcher"
    job.run_mode = "forever"
    job.status = "running"
    job.entrypoint = "main.py"
    job.python_version = "3.12"
    job.auto_pull = True
    job.restart_on_crash = True
    job.cron_expression = None
    job.repo = MagicMock()
    job.repo.github_url = "https://github.com/u/r"
    with patch("app.telegram_bot.db_mod") as mock_db, \
         patch("app.telegram_bot.process_manager") as mock_pm:
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = job
        mock_pm.get_status.return_value = "running"
        await bot_mod.cmd_info(update, ctx)
    text = update.message.reply_text.call_args[0][0]
    assert "fetcher" in text
    assert "https://github.com/u/r" in text
    assert "main.py" in text
    assert "3.12" in text


@pytest.mark.asyncio
async def test_run_cron_job_sends_started_reply():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context(args=["2"])
    job = MagicMock()
    job.id = 2
    job.name = "report"
    job.run_mode = "cron"
    job.notification_url = None
    with patch("app.telegram_bot.db_mod") as mock_db, \
         patch("app.telegram_bot._build_cmd", return_value=["python", "main.py"]), \
         patch("app.telegram_bot._build_env", return_value={}), \
         patch("asyncio.create_task"):
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = job
        await bot_mod.cmd_run(update, ctx)
    assert "▶️" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_run_forever_job_returns_error():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context(args=["1"])
    job = MagicMock()
    job.id = 1
    job.run_mode = "forever"
    with patch("app.telegram_bot.db_mod") as mock_db:
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = job
        await bot_mod.cmd_run(update, ctx)
    assert "/run only works on cron jobs" in update.message.reply_text.call_args[0][0]


# /restart tests

@pytest.mark.asyncio
async def test_restart_stopped_forever_job():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context(args=["1"])
    job = MagicMock()
    job.id = 1
    job.name = "fetcher"
    job.run_mode = "forever"
    job.status = "stopped"
    job.restart_on_crash = True
    job.notification_url = None
    job.notify_on_stderr = False
    with patch("app.telegram_bot.db_mod") as mock_db, \
         patch("app.telegram_bot.process_manager") as mock_pm, \
         patch("app.telegram_bot._build_cmd", return_value=["python", "main.py"]), \
         patch("app.telegram_bot._build_env", return_value={}):
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = job
        mock_pm.get_status.return_value = "stopped"
        mock_pm.start = AsyncMock()
        await bot_mod.cmd_restart(update, ctx)
        mock_pm.start.assert_called_once()
    assert "🔄 Restarted" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_restart_running_forever_job():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context(args=["1"])
    job = MagicMock()
    job.id = 1
    job.name = "fetcher"
    job.run_mode = "forever"
    job.status = "running"
    job.restart_on_crash = True
    job.notification_url = None
    job.notify_on_stderr = False
    with patch("app.telegram_bot.db_mod") as mock_db, \
         patch("app.telegram_bot.process_manager") as mock_pm, \
         patch("app.telegram_bot._build_cmd", return_value=["python", "main.py"]), \
         patch("app.telegram_bot._build_env", return_value={}):
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = job
        mock_pm.get_status.return_value = "running"
        mock_pm.stop = AsyncMock()
        mock_pm.start = AsyncMock()
        await bot_mod.cmd_restart(update, ctx)
        mock_pm.stop.assert_called_once_with(1)
        mock_pm.start.assert_called_once()
    assert "🔄 Restarting" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_restart_cron_job_returns_error():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context(args=["2"])
    job = MagicMock()
    job.id = 2
    job.run_mode = "cron"
    with patch("app.telegram_bot.db_mod") as mock_db:
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = job
        await bot_mod.cmd_restart(update, ctx)
    assert "/restart only works on forever jobs" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_restart_nonexistent_job_returns_error():
    _set_allowed(111)
    update = _make_update(user_id=111)
    ctx = _make_context(args=["99"])
    with patch("app.telegram_bot.db_mod") as mock_db:
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = None
        await bot_mod.cmd_restart(update, ctx)
    assert "❌ Job 99 not found" in update.message.reply_text.call_args[0][0]