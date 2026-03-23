"""Tests for pinterest_export.exporter."""

import json
from pathlib import Path

from pinterest_export.exporter import export_json, export_markdown
from pinterest_export.models import Pin


def _make_pins() -> list[Pin]:
    return [
        Pin(
            id="1",
            image_url="https://i.pinimg.com/originals/aa/bb/cc.jpg",
            title="Vintage Chair",
            description="A lovely old chair",
            link="https://www.pinterest.com/pin/1/",
            board_url="https://www.pinterest.com/user/board/",
        ),
        Pin(
            id="2",
            image_url="https://i.pinimg.com/originals/dd/ee/ff.jpg",
            title="",
            description="",
            link="https://www.pinterest.com/pin/2/",
            board_url="https://www.pinterest.com/user/board/",
        ),
    ]


def test_export_json_creates_file(tmp_path):
    pins = _make_pins()
    out = tmp_path / "board.json"
    export_json(pins, "https://www.pinterest.com/user/board/", out)

    assert out.exists()
    data = json.loads(out.read_text())
    assert data["pin_count"] == 2
    assert len(data["pins"]) == 2
    assert data["pins"][0]["title"] == "Vintage Chair"


def test_export_json_includes_local_paths(tmp_path):
    pins = _make_pins()
    out = tmp_path / "board.json"
    fake_paths = {"1": Path("/tmp/cache/abc.jpg")}
    export_json(pins, "https://www.pinterest.com/user/board/", out, image_paths=fake_paths)

    data = json.loads(out.read_text())
    assert data["pins"][0]["local_image_path"] == "/tmp/cache/abc.jpg"
    assert "local_image_path" not in data["pins"][1]


def test_export_markdown_creates_file(tmp_path):
    pins = _make_pins()
    out = tmp_path / "board.md"
    export_markdown(pins, "https://www.pinterest.com/user/board/", out)

    assert out.exists()
    content = out.read_text()
    assert "# Pinterest Board Export" in content
    assert "Vintage Chair" in content
    assert "Pin count:** 2" in content


def test_export_markdown_no_title_fallback(tmp_path):
    pins = _make_pins()
    out = tmp_path / "board.md"
    export_markdown(pins, "https://www.pinterest.com/user/board/", out)

    content = out.read_text()
    assert "(no title)" in content


def test_export_markdown_includes_vision_metadata(tmp_path):
    pins = _make_pins()
    pins[0].extra = {
        "vision_description": "A cozy vintage chair in warm daylight.",
        "vision_tags": ["vintage", "chair", "cozy"],
        "vision_colors": ["#A67C52", "#F5EBDD"],
        "vision_style": ["rustic", "classic"],
        "vision_mood": "warm",
    }

    out = tmp_path / "board.md"
    export_markdown(pins, "https://www.pinterest.com/user/board/", out)

    content = out.read_text()
    assert "Vision description" in content
    assert "vintage, chair, cozy" in content
    assert "#A67C52, #F5EBDD" in content
    assert "rustic, classic" in content
    assert "Vision mood:** warm" in content
