"""Retry utilities with exponential back-off and jitter for HTTP operations."""

import asyncio
import logging
import random
from typing import TypeVar, Callable, Awaitable

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Status codes that warrant a retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _jitter(base: float, factor: float = 0.25) -> float:
    """Return *base* ± factor * base of random jitter."""
    spread = base * factor
    return base + random.uniform(-spread, spread)


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (
        httpx.TimeoutException,
        httpx.NetworkError,
    ),
    label: str = "operation",
) -> T:
    """Retry *fn* up to *max_attempts* times with exponential back-off + jitter.

    Args:
        fn: Async callable to attempt.
        max_attempts: Total number of attempts (including the first).
        base_delay: Initial wait between retries in seconds.
        max_delay: Cap on calculated delay.
        backoff_factor: Multiplier applied to *base_delay* per retry.
        retryable_exceptions: Exception types that trigger a retry.
        label: Human-readable label for log messages.

    Returns:
        The return value of *fn* on success.

    Raises:
        The last exception raised by *fn* if all attempts are exhausted.
    """
    last_exc: Exception | None = None
    delay = base_delay

    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status not in RETRYABLE_STATUS_CODES or attempt == max_attempts:
                raise

            # Respect Retry-After header when present (Pinterest / Cloudflare)
            retry_after_raw = exc.response.headers.get("Retry-After")
            if retry_after_raw is not None:
                try:
                    wait = float(retry_after_raw)
                except ValueError:
                    wait = delay
            else:
                wait = delay

            wait = min(wait, max_delay)
            logger.warning(
                "%s — HTTP %d on attempt %d/%d, retrying in %.1fs",
                label, status, attempt, max_attempts, wait,
            )
            await asyncio.sleep(_jitter(wait))
            delay = min(delay * backoff_factor, max_delay)
            last_exc = exc

        except retryable_exceptions as exc:  # type: ignore[misc]
            if attempt == max_attempts:
                raise

            wait = min(delay, max_delay)
            logger.warning(
                "%s — %s on attempt %d/%d, retrying in %.1fs",
                label, type(exc).__name__, attempt, max_attempts, wait,
            )
            await asyncio.sleep(_jitter(wait))
            delay = min(delay * backoff_factor, max_delay)
            last_exc = exc

    # Should never reach here, but satisfies type checker
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"{label}: exhausted {max_attempts} attempts")  # pragma: no cover
