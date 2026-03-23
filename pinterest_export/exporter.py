"""JSON and Markdown export for scraped Pinterest boards."""

import json
from datetime import datetime, timezone
from pathlib import Path

from pinterest_export.models import Pin


def _pin_to_dict(pin: Pin, image_paths: dict[str, Path] | None = None) -> dict:
    """Serialize a Pin to a JSON-compatible dict, optionally injecting local image path."""
    d = pin.to_dict()
    if image_paths and pin.id in image_paths:
        d["local_image_path"] = str(image_paths[pin.id])
    return d


def export_json(
    pins: list[Pin],
    board_url: str,
    output_path: Path,
    image_paths: dict[str, Path] | None = None,
) -> None:
    """Write board.json — full pin metadata in a structured JSON file.

    Args:
        pins: All scraped pins.
        board_url: The source board URL.
        output_path: Destination file (e.g. output/board.json).
        image_paths: Optional mapping of pin_id → local cached image path.
    """
    payload = {
        "board_url": board_url,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "pin_count": len(pins),
        "pins": [_pin_to_dict(p, image_paths) for p in pins],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def export_markdown(
    pins: list[Pin],
    board_url: str,
    output_path: Path,
    image_paths: dict[str, Path] | None = None,
) -> None:
    """Write board.md — a human-readable context file optimised for downstream LLM use.

    The Markdown is structured so an LLM can easily consume the board's visual
    catalogue (titles, descriptions, image URLs, and optional local paths) to
    assist with design, mood-board, or creative tasks.

    Args:
        pins: All scraped pins.
        board_url: The source board URL.
        output_path: Destination file (e.g. output/board.md).
        image_paths: Optional mapping of pin_id → local cached image path.
    """
    lines: list[str] = [
        "# Pinterest Board Export",
        "",
        f"**Source:** {board_url}  ",
        f"**Exported:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Pin count:** {len(pins)}",
        "",
        "---",
        "",
    ]

    for i, pin in enumerate(pins, 1):
        lines.append(f"## Pin {i} — {pin.title or '(no title)'}")
        lines.append("")
        if pin.description:
            lines.append(f"**Description:** {pin.description}")
            lines.append("")
        lines.append(f"- **Pinterest link:** {pin.link}")
        lines.append(f"- **Image URL:** {pin.image_url}")
        if image_paths and pin.id in image_paths:
            lines.append(f"- **Local image:** {image_paths[pin.id]}")

        vision_description = pin.extra.get("vision_description")
        if vision_description:
            lines.append(f"- **Vision description:** {vision_description}")

        vision_tags = pin.extra.get("vision_tags")
        if isinstance(vision_tags, list) and vision_tags:
            lines.append(f"- **Vision tags:** {', '.join(str(tag) for tag in vision_tags)}")

        vision_colors = pin.extra.get("vision_colors")
        if isinstance(vision_colors, list) and vision_colors:
            lines.append(f"- **Vision colors:** {', '.join(str(color) for color in vision_colors)}")

        vision_style = pin.extra.get("vision_style")
        if isinstance(vision_style, list) and vision_style:
            lines.append(f"- **Vision style:** {', '.join(str(style) for style in vision_style)}")

        vision_mood = pin.extra.get("vision_mood")
        if vision_mood:
            lines.append(f"- **Vision mood:** {vision_mood}")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
