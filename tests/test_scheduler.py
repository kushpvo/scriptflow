import sys
import asyncio
import pytest
from app.scheduler import add_cron_job, remove_cron_job, get_scheduler


@pytest.fixture(autouse=True)
def fresh_scheduler(tmp_data_dir):
    import app.scheduler as sched_mod
    sched_mod._scheduler = None
    yield
    if sched_mod._scheduler and sched_mod._scheduler.running:
        sched_mod._scheduler.shutdown(wait=False)
    sched_mod._scheduler = None


def test_add_and_remove_cron_job(tmp_data_dir):
    cmd = [sys.executable, "-c", "print('hi')"]
    add_cron_job(1, "0 9 * * *", cmd, env={}, notification_url=None)
    sched = get_scheduler()
    assert sched.get_job("job_1") is not None
    remove_cron_job(1)
    assert sched.get_job("job_1") is None


def test_add_invalid_cron_raises(tmp_data_dir):
    with pytest.raises(ValueError):
        add_cron_job(2, "bad expression", [], env={}, notification_url=None)


def test_remove_nonexistent_job_is_noop(tmp_data_dir):
    remove_cron_job(999)  # should not raise