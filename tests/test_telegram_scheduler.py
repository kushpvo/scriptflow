from unittest.mock import MagicMock, patch
from app.scheduler import pause_cron_job, resume_cron_job


def test_pause_cron_job_calls_scheduler():
    with patch("app.scheduler.get_scheduler") as mock_get:
        mock_sched = MagicMock()
        mock_get.return_value = mock_sched
        pause_cron_job(7)
        mock_sched.pause_job.assert_called_once_with("job_7")


def test_resume_cron_job_calls_scheduler():
    with patch("app.scheduler.get_scheduler") as mock_get:
        mock_sched = MagicMock()
        mock_get.return_value = mock_sched
        resume_cron_job(7)
        mock_sched.resume_job.assert_called_once_with("job_7")
