import apprise
import time
import logging

logger = logging.getLogger(__name__)

_stderr_last_notified: dict[int, float] = {}
STDERR_RATE_LIMIT_SECS = 60


async def send_notification(url: str, title: str, body: str) -> None:
    if not url:
        return
    try:
        ap = apprise.Apprise()
        ap.add(url)
        await ap.async_notify(title=title, body=body)
    except Exception as e:
        logger.warning(f"Notification failed: {e}")


def should_notify_stderr(job_id: int) -> bool:
    now = time.monotonic()
    last = _stderr_last_notified.get(job_id, 0)
    if now - last >= STDERR_RATE_LIMIT_SECS:
        _stderr_last_notified[job_id] = now
        return True
    return False


def reset_stderr_rate_limit(job_id: int) -> None:
    _stderr_last_notified.pop(job_id, None)