"""Tests for pinterest_export.url_parser."""

import pytest
from pinterest_export.url_parser import parse_board_url


class TestParseValidURLs:
    def test_full_url(self):
        r = parse_board_url("https://pinterest.com/johndoe/my-board")
        assert r["canonical"] == "https://www.pinterest.com/johndoe/my-board/"
        assert r["username"] == "johndoe"
        assert r["boardname"] == "my-board"

    def test_www_url_with_trailing_slash(self):
        r = parse_board_url("https://www.pinterest.com/johndoe/my-board/")
        assert r["canonical"] == "https://www.pinterest.com/johndoe/my-board/"

    def test_no_scheme(self):
        r = parse_board_url("pinterest.com/johndoe/my-board")
        assert r["username"] == "johndoe"
        assert r["boardname"] == "my-board"

    def test_relative_path(self):
        r = parse_board_url("/johndoe/my-board")
        assert r["canonical"] == "https://www.pinterest.com/johndoe/my-board/"

    def test_raw_preserved(self):
        raw = "  https://pinterest.com/a/b  "
        r = parse_board_url(raw)
        assert r["raw"] == raw

    def test_country_subdomain(self):
        r = parse_board_url("https://nl.pinterest.com/user/board/")
        assert r["canonical"] == "https://www.pinterest.com/user/board/"


class TestParseInvalidURLs:
    def test_empty(self):
        with pytest.raises(ValueError, match="Empty"):
            parse_board_url("")

    def test_short_link(self):
        with pytest.raises(ValueError, match=r"pin\.it"):
            parse_board_url("https://pin.it/abc123")

    def test_pin_url(self):
        with pytest.raises(ValueError, match="single pin"):
            parse_board_url("https://www.pinterest.com/pin/123456789/")

    def test_missing_boardname(self):
        with pytest.raises(ValueError, match="Could not extract"):
            parse_board_url("https://www.pinterest.com/johndoe/")

    def test_not_pinterest(self):
        with pytest.raises(ValueError, match="Not a Pinterest"):
            parse_board_url("https://example.com/foo/bar")

    def test_deceptive_hostname_containing_pinterest(self):
        """Regression: notpinterest.com must be rejected (not just substring match)."""
        with pytest.raises(ValueError, match="Not a Pinterest"):
            parse_board_url("https://notpinterest.com/johndoe/boardname")

    def test_reserved_path(self):
        with pytest.raises(ValueError, match="reserved"):
            parse_board_url("https://www.pinterest.com/search/pins")
