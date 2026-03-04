"""Tests for pinterest_export.vision."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pinterest_export.models import Pin
from pinterest_export.vision import analyze_pin, analyze_pins


def _make_pin(id_: str = "1") -> Pin:
    return Pin(
        id=id_,
        image_url="https://i.pinimg.com/originals/ab/cd/ef.jpg",
        title="Test pin",
        description="",
        link=f"https://www.pinterest.com/pin/{id_}/",
        board_url="https://www.pinterest.com/user/board/",
    )


@pytest.mark.asyncio
async def test_analyze_pin_returns_normalized_payload():
    pin = _make_pin()

    fake_http_response = MagicMock()
    fake_http_response.raise_for_status = MagicMock()
    fake_http_response.content = b"fake-image-bytes"
    fake_http_response.headers = {"content-type": "image/jpeg"}

    class FakeModel:
        def generate_content(self, parts):
            assert parts
            return SimpleNamespace(
                text=(
                    '{"description":"A wooden chair","tags":["chair","wood"],'
                    '"dominant_colors":["#A67C52"],"style_keywords":["rustic"],'
                    '"mood":"cozy"}'
                )
            )

    fake_genai = SimpleNamespace(
        configure=MagicMock(),
        GenerativeModel=MagicMock(return_value=FakeModel()),
    )

    with patch("httpx.AsyncClient") as mock_client_cls, patch("pinterest_export.vision.genai", fake_genai):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=fake_http_response)
        mock_client_cls.return_value = mock_client

        result = await analyze_pin(pin, api_key="test-key")

    assert result["description"] == "A wooden chair"
    assert result["tags"] == ["chair", "wood"]
    assert result["dominant_colors"] == ["#A67C52"]
    assert result["style_keywords"] == ["rustic"]
    assert result["mood"] == "cozy"


@pytest.mark.asyncio
async def test_analyze_pin_returns_empty_dict_on_http_error():
    pin = _make_pin()

    fake_genai = SimpleNamespace(
        configure=MagicMock(),
        GenerativeModel=MagicMock(),
    )

    with patch("httpx.AsyncClient") as mock_client_cls, patch("pinterest_export.vision.genai", fake_genai):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=RuntimeError("boom"))
        mock_client_cls.return_value = mock_client

        result = await analyze_pin(pin, api_key="test-key")

    assert result == {}


@pytest.mark.asyncio
async def test_analyze_pins_mutates_pin_extra_fields():
    pins = [_make_pin("1"), _make_pin("2")]

    responses = [
        {
            "description": "First",
            "tags": ["one"],
            "dominant_colors": ["#111111"],
            "style_keywords": ["modern"],
            "mood": "calm",
        },
        {},
    ]

    mock_analyze_pin = AsyncMock(side_effect=responses)
    with patch("pinterest_export.vision.analyze_pin", mock_analyze_pin):
        await analyze_pins(pins, api_key="test-key", concurrency=2)

    assert pins[0].extra["vision_description"] == "First"
    assert pins[0].extra["vision_tags"] == ["one"]
    assert pins[0].extra["vision_colors"] == ["#111111"]
    assert pins[0].extra["vision_style"] == ["modern"]
    assert pins[0].extra["vision_mood"] == "calm"

    assert pins[1].extra["vision_description"] == ""
    assert pins[1].extra["vision_tags"] == []
    assert pins[1].extra["vision_colors"] == []
    assert pins[1].extra["vision_style"] == []
    assert pins[1].extra["vision_mood"] == ""
