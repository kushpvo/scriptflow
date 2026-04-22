import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.process_manager import ProcessManager, JobProcess


@pytest.mark.asyncio
async def test_stop_clean_exit():
    pm = ProcessManager()
    jp = pm._get_or_create(1)
    jp.status = "running"
    jp.proc = MagicMock()
    jp.proc.wait = AsyncMock(return_value=0)
    await pm.stop(1)
    assert jp.status == "stopped"
    jp.proc.terminate.assert_called_once()


@pytest.mark.asyncio
async def test_stop_sigkill_on_timeout():
    pm = ProcessManager()
    jp = pm._get_or_create(2)
    jp.status = "running"
    jp.proc = MagicMock()
    jp.proc.wait = AsyncMock(side_effect=[asyncio.TimeoutError, 0])
    jp.proc.kill = MagicMock()
    await pm.stop(2)
    jp.proc.kill.assert_called_once()
    assert jp.status == "stopped"


def test_get_status_idle_job():
    pm = ProcessManager()
    assert pm.get_status(999) == "idle"


@pytest.mark.asyncio
async def test_start_already_running_is_noop():
    pm = ProcessManager()
    jp = pm._get_or_create(3)
    jp.status = "running"
    # start should not restart an already-running job
    await pm.start(3, ["echo"], {}, False, None, False)
    assert jp.status == "running"
