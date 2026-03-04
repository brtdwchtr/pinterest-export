"""Vision analysis for Pinterest pins using Gemini Flash."""

import asyncio
import json
import logging
import re
from typing import Any

import httpx

from pinterest_export.models import Pin

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - exercised when dependency is unavailable
    genai = None

logger = logging.getLogger(__name__)

_VISION_PROMPT = """Analyze this Pinterest image and return only valid JSON.

Required JSON schema:
{
  "description": "short visual description",
  "tags": ["5 to 10 concise tags"],
  "dominant_colors": ["hex colors like #AABBCC"],
  "style_keywords": ["style terms"],
  "mood": "single mood word or short phrase"
}

Rules:
- Return JSON only (no markdown, no prose, no code fences).
- Keep tags and style_keywords concise and lowercase where natural.
- dominant_colors must be hex values prefixed with #.
"""


def _response_text(response: Any) -> str:
    """Extract text from a Gemini response object."""
    try:
        text = response.text or ""
        if text:
            return text
    except Exception:
        pass

    chunks: list[str] = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", []) if content else []
        for part in parts:
            value = getattr(part, "text", None)
            if value:
                chunks.append(value)
    return "\n".join(chunks).strip()


def _extract_json(text: str) -> dict[str, Any]:
    """Parse JSON from a Gemini response string."""
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}

    snippet = cleaned[start : end + 1]
    try:
        parsed = json.loads(snippet)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _string_list(value: Any) -> list[str]:
    """Normalize an arbitrary value to a list of non-empty strings."""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize Gemini JSON payload to expected keys and types."""
    return {
        "description": str(payload.get("description", "")).strip(),
        "tags": _string_list(payload.get("tags")),
        "dominant_colors": _string_list(payload.get("dominant_colors")),
        "style_keywords": _string_list(payload.get("style_keywords")),
        "mood": str(payload.get("mood", "")).strip(),
    }


async def analyze_pin(pin: Pin, api_key: str) -> dict:
    """Analyze a single pin image with Gemini Flash and return parsed JSON metadata."""
    if not api_key:
        logger.warning("Skipping vision analysis for pin %s: missing API key", pin.id)
        return {}

    if not pin.image_url:
        logger.warning("Skipping vision analysis for pin %s: missing image URL", pin.id)
        return {}

    if genai is None:
        logger.warning("Skipping vision analysis for pin %s: google-generativeai is not installed", pin.id)
        return {}

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.pinterest.com/",
    }

    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            response = await client.get(pin.image_url, timeout=20)
            response.raise_for_status()

        mime_type = response.headers.get("content-type", "image/jpeg").split(";", 1)[0]
        image_part = {
            "mime_type": mime_type if mime_type.startswith("image/") else "image/jpeg",
            "data": response.content,
        }

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        gemini_response = await asyncio.to_thread(model.generate_content, [_VISION_PROMPT, image_part])

        text = _response_text(gemini_response)
        if not text:
            logger.warning("Empty Gemini response for pin %s", pin.id)
            return {}

        payload = _extract_json(text)
        if not payload:
            logger.warning("Unable to parse Gemini JSON for pin %s", pin.id)
            return {}

        return _normalize_payload(payload)
    except Exception as exc:
        logger.warning("Vision analysis failed for pin %s: %s", pin.id, exc)
        return {}


def _apply_vision_metadata(pin: Pin, vision: dict[str, Any]) -> None:
    """Persist normalized vision fields into pin.extra."""
    pin.extra["vision_description"] = str(vision.get("description", "")).strip()
    pin.extra["vision_tags"] = _string_list(vision.get("tags"))
    pin.extra["vision_colors"] = _string_list(vision.get("dominant_colors"))
    pin.extra["vision_style"] = _string_list(vision.get("style_keywords"))
    pin.extra["vision_mood"] = str(vision.get("mood", "")).strip()


async def analyze_pins(pins: list[Pin], api_key: str, concurrency: int = 5) -> None:
    """Analyze pins in parallel and mutate each pin with vision metadata."""
    if concurrency <= 0:
        concurrency = 1

    sem = asyncio.Semaphore(concurrency)

    async def _analyze_one(pin: Pin) -> None:
        async with sem:
            vision = await analyze_pin(pin, api_key)
            _apply_vision_metadata(pin, vision)

    await asyncio.gather(*[_analyze_one(pin) for pin in pins])
