"""Tests for the Pin dataclass (issue #3)."""

import pytest
from pinterest_export.models import Pin


def _make_pin(**kwargs) -> Pin:
    defaults = dict(
        id="123456789",
        image_url="https://i.pinimg.com/736x/ab/cd/ef/image.jpg",
        title="Beautiful sunset",
        description="A stunning golden-hour photo",
        link="https://www.pinterest.com/pin/123456789/",
        board_url="https://www.pinterest.com/user/board/",
    )
    defaults.update(kwargs)
    return Pin(**defaults)


class TestPinDataclass:
    def test_required_fields(self):
        pin = _make_pin()
        assert pin.id == "123456789"
        assert pin.image_url == "https://i.pinimg.com/736x/ab/cd/ef/image.jpg"
        assert pin.title == "Beautiful sunset"
        assert pin.description == "A stunning golden-hour photo"
        assert pin.link == "https://www.pinterest.com/pin/123456789/"
        assert pin.board_url == "https://www.pinterest.com/user/board/"

    def test_extra_defaults_to_empty_dict(self):
        pin = _make_pin()
        assert pin.extra == {}

    def test_extra_is_not_shared_between_instances(self):
        pin1 = _make_pin()
        pin2 = _make_pin()
        pin1.extra["key"] = "value"
        assert "key" not in pin2.extra

    def test_to_dict_includes_all_core_fields(self):
        pin = _make_pin()
        d = pin.to_dict()
        assert d["id"] == "123456789"
        assert d["image_url"] == "https://i.pinimg.com/736x/ab/cd/ef/image.jpg"
        assert d["title"] == "Beautiful sunset"
        assert d["description"] == "A stunning golden-hour photo"
        assert d["link"] == "https://www.pinterest.com/pin/123456789/"
        assert d["board_url"] == "https://www.pinterest.com/user/board/"

    def test_to_dict_merges_extra(self):
        pin = _make_pin(extra={"theme": "nature", "color": "warm"})
        d = pin.to_dict()
        assert d["theme"] == "nature"
        assert d["color"] == "warm"

    def test_empty_strings_allowed(self):
        """Scraped pins often have missing titles/descriptions."""
        pin = _make_pin(title="", description="", image_url="")
        assert pin.title == ""
        assert pin.description == ""
        assert pin.image_url == ""

    def test_pin_equality(self):
        pin1 = _make_pin()
        pin2 = _make_pin()
        assert pin1 == pin2

    def test_pin_inequality_on_id(self):
        pin1 = _make_pin(id="111")
        pin2 = _make_pin(id="222")
        assert pin1 != pin2
