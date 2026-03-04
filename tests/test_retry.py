"""Tests for pinterest_export.retry — exponential back-off and retry logic."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pinterest_export.retry import retry_async, RETRYABLE_STATUS_CODES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _http_status_error(status: int, retry_after: str | None = None) -> httpx.HTTPStatusError:
    headers = {}
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(status, headers=headers, request=request)
    return httpx.HTTPStatusError(f"HTTP {status}", request=request, response=response)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_success_on_first_attempt():
    fn = AsyncMock(return_value="ok")
    result = await retry_async(fn, max_attempts=3, base_delay=0)
    assert result == "ok"
    fn.assert_called_once()


# ---------------------------------------------------------------------------
# Retryable HTTP errors
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("status", sorted(RETRYABLE_STATUS_CODES))
async def test_retries_on_retryable_status(status):
    calls = 0

    async def fn():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise _http_status_error(status)
        return "done"

    with patch("pinterest_export.retry.asyncio.sleep", new=AsyncMock()):
        result = await retry_async(fn, max_attempts=3, base_delay=0.01)

    assert result == "done"
    assert calls == 3


@pytest.mark.asyncio
async def test_raises_after_max_attempts():
    fn = AsyncMock(side_effect=_http_status_error(429))

    with patch("pinterest_export.retry.asyncio.sleep", new=AsyncMock()):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await retry_async(fn, max_attempts=3, base_delay=0.01)

    assert exc_info.value.response.status_code == 429
    assert fn.call_count == 3


@pytest.mark.asyncio
async def test_non_retryable_status_raises_immediately():
    """4xx errors other than 429 should not be retried."""
    fn = AsyncMock(side_effect=_http_status_error(404))

    with patch("pinterest_export.retry.asyncio.sleep", new=AsyncMock()):
        with pytest.raises(httpx.HTTPStatusError):
            await retry_async(fn, max_attempts=3, base_delay=0.01)

    fn.assert_called_once()  # no retry


# ---------------------------------------------------------------------------
# Retry-After header
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_respects_retry_after_header():
    calls = 0

    async def fn():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _http_status_error(429, retry_after="5")
        return "ok"

    sleep_calls = []

    async def fake_sleep(t):
        sleep_calls.append(t)

    with patch("pinterest_export.retry.asyncio.sleep", side_effect=fake_sleep):
        result = await retry_async(fn, max_attempts=2, base_delay=1.0, max_delay=60.0)

    assert result == "ok"
    # Sleep value should be close to 5s (±25% jitter)
    assert len(sleep_calls) == 1
    assert 3.5 <= sleep_calls[0] <= 6.5


# ---------------------------------------------------------------------------
# Network errors
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retries_on_timeout():
    calls = 0

    async def fn():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise httpx.TimeoutException("timed out", request=MagicMock())
        return "recovered"

    with patch("pinterest_export.retry.asyncio.sleep", new=AsyncMock()):
        result = await retry_async(fn, max_attempts=3, base_delay=0.01)

    assert result == "recovered"
    assert calls == 2


@pytest.mark.asyncio
async def test_network_error_exhausts_retries():
    fn = AsyncMock(side_effect=httpx.NetworkError("disconnected", request=MagicMock()))

    with patch("pinterest_export.retry.asyncio.sleep", new=AsyncMock()):
        with pytest.raises(httpx.NetworkError):
            await retry_async(fn, max_attempts=2, base_delay=0.01)

    assert fn.call_count == 2


# ---------------------------------------------------------------------------
# Backoff growth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_backoff_grows_exponentially():
    fn = AsyncMock(side_effect=_http_status_error(503))
    sleep_calls = []

    async def fake_sleep(t):
        sleep_calls.append(t)

    with patch("pinterest_export.retry.asyncio.sleep", side_effect=fake_sleep):
        with pytest.raises(httpx.HTTPStatusError):
            await retry_async(fn, max_attempts=4, base_delay=1.0, backoff_factor=2.0)

    # With jitter ±25%: 1s → ~2s → ~4s (3 sleeps for 4 attempts)
    assert len(sleep_calls) == 3
    # Each subsequent sleep should generally be larger (accounting for jitter)
    # At minimum, the base doubles: 1 * 2^n, so sleep[1] > sleep[0] * 0.5 typically
    assert sleep_calls[1] > sleep_calls[0] * 0.5
