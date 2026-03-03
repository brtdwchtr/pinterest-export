"""Data models for pinterest-export."""

from dataclasses import dataclass, field


@dataclass
class Pin:
    """Represents a single Pinterest pin extracted from a board.

    Attributes:
        id: The unique Pinterest pin ID (numeric string).
        image_url: Full-resolution image URL (highest-res from srcset, or src fallback).
        title: Pin title / image alt text.
        description: Pin description (empty string when not available on board view).
        link: Canonical Pinterest pin URL (https://www.pinterest.com/pin/<id>/).
        board_url: The source board URL this pin was scraped from.
    """

    id: str
    image_url: str
    title: str
    description: str
    link: str
    board_url: str
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary (JSON-compatible)."""
        return {
            "id": self.id,
            "image_url": self.image_url,
            "title": self.title,
            "description": self.description,
            "link": self.link,
            "board_url": self.board_url,
            **self.extra,
        }
