"""Tests for pinterest_export.image_cache."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pinterest_export.image_cache import (
    DEFAULT_RATE_LIMIT,
    _cache_key,
    _extension,
    download_pins,
)
from pinterest_export.models import Pin


def _make_pin(id_="1", image_url="https://i.pinimg.com/originals/ab/cd/ef.jpg") -> Pin:
    return Pin(
        id=id_,
        image_url=image_url,
        title="Test",
        description="",
        link=f"https://www.pinterest.com/pin/{id_}/",
        board_url="https://www.pinterest.com/user/board/",
    )


def test_cache_key_deterministic():
    url = "https://i.pinimg.com/originals/ab/cd/ef.jpg"
    assert _cache_key(url) == _cache_key(url)
    assert len(_cache_key(url)) == 24


def test_cache_key_different_urls():
    assert _cache_key("https://example.com/a.jpg") != _cache_key("https://example.com/b.jpg")


def test_extension_known():
    assert _extension("https://example.com/img.png") == ".png"
    assert _extension("https://example.com/img.webp") == ".webp"


def test_extension_unknown_defaults_to_jpg():
    assert _extension("https://example.com/img.bmp") == ".jpg"
    assert _extension("https://example.com/no-ext") == ".jpg"


@pytest.mark.asyncio
async def test_download_pins_skips_cached(tmp_path):
    pin = _make_pin()
    key = _cache_key(pin.image_url)
    ext = _extension(pin.image_url)
    cached_file = tmp_path / f"{key}{ext}"
    cached_file.write_bytes(b"fake-image-data")

    result = await download_pins([pin], cache_dir=tmp_path, rate_limit=0)
    assert pin.id in result
    assert result[pin.id] == cached_file


@pytest.mark.asyncio
async def test_download_pins_downloads_missing(tmp_path):
    pin = _make_pin()

    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.content = b"real-image-bytes"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=fake_response)
        mock_client_cls.return_value = mock_client

        result = await download_pins([pin], cache_dir=tmp_path, rate_limit=0)

    assert pin.id in result
    assert result[pin.id].read_bytes() == b"real-image-bytes"
