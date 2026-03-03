"""Async image downloader with local SHA256-based cache."""

import asyncio
import hashlib
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx

from pinterest_export.models import Pin

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "pinterest-export" / "images"
MAX_CONCURRENCY = 5
DEFAULT_RATE_LIMIT = 0.3  # seconds between requests per semaphore slot


def _cache_key(image_url: str) -> str:
    """Return a short SHA256 hex string for the image URL."""
    return hashlib.sha256(image_url.encode()).hexdigest()[:24]


def _extension(image_url: str) -> str:
    """Extract file extension from URL, default to .jpg."""
    path = urlparse(image_url).path
    ext = Path(path).suffix.lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"} else ".jpg"


async def _download_one(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    pin: Pin,
    cache_dir: Path,
    rate_limit: float,
) -> tuple[str, Path | None]:
    """Download a single pin image. Returns (pin.id, local_path | None)."""
    key = _cache_key(pin.image_url)
    ext = _extension(pin.image_url)
    dest = cache_dir / f"{key}{ext}"

    if dest.exists():
        logger.debug("Cache hit for pin %s → %s", pin.id, dest)
        return pin.id, dest

    async with sem:
        await asyncio.sleep(rate_limit)
        try:
            resp = await client.get(pin.image_url, follow_redirects=True, timeout=20)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            logger.debug("Downloaded pin %s → %s", pin.id, dest)
            return pin.id, dest
        except Exception as exc:
            logger.warning("Failed to download pin %s (%s): %s", pin.id, pin.image_url, exc)
            return pin.id, None


async def download_pins(
    pins: list[Pin],
    cache_dir: Path = DEFAULT_CACHE_DIR,
    rate_limit: float = DEFAULT_RATE_LIMIT,
    max_concurrency: int = MAX_CONCURRENCY,
) -> dict[str, Path]:
    """Download images for a list of pins to a local cache directory.

    Args:
        pins: List of Pin objects whose images should be downloaded.
        cache_dir: Directory to store downloaded images (created if absent).
        rate_limit: Seconds to wait between requests per concurrent slot.
        max_concurrency: Maximum simultaneous HTTP downloads.

    Returns:
        A mapping of pin_id → local Path for successfully downloaded images.
        Pins whose downloads failed are omitted from the result.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(max_concurrency)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.pinterest.com/",
    }

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        tasks = [
            _download_one(client, sem, pin, cache_dir, rate_limit) for pin in pins
        ]
        results = await asyncio.gather(*tasks)

    return {pin_id: path for pin_id, path in results if path is not None}
