import pytest
from unittest.mock import AsyncMock, patch
from app.notifications import send_notification, should_notify_stderr, reset_stderr_rate_limit


@pytest.mark.asyncio
async def test_send_notification_calls_apprise():
    with patch("apprise.Apprise") as MockApprise:
        instance = MockApprise.return_value
        instance.async_notify = AsyncMock(return_value=True)
        await send_notification("tgram://fake/123", "title", "body")
        instance.async_notify.assert_called_once()


@pytest.mark.asyncio
async def test_send_notification_empty_url_is_noop():
    with patch("apprise.Apprise") as MockApprise:
        instance = MockApprise.return_value
        instance.async_notify = AsyncMock(return_value=True)
        await send_notification("", "title", "body")
        instance.async_notify.assert_not_called()


@pytest.mark.asyncio
async def test_send_notification_bad_url_does_not_raise():
    await send_notification("notascheme://garbage", "t", "b")


def test_stderr_rate_limit_allows_first():
    reset_stderr_rate_limit(1)
    assert should_notify_stderr(1) is True


def test_stderr_rate_limit_blocks_second():
    reset_stderr_rate_limit(2)
    should_notify_stderr(2)  # first — allowed
    assert should_notify_stderr(2) is False  # second — blocked


def test_stderr_rate_limit_different_jobs_independent():
    reset_stderr_rate_limit(3)
    reset_stderr_rate_limit(4)
    assert should_notify_stderr(3) is True
    assert should_notify_stderr(4) is True  # different job — not blocked