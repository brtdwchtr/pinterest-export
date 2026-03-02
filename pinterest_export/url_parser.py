"""Pinterest board URL parsing and normalization."""

import re
from urllib.parse import urlparse


def parse_board_url(url: str) -> dict:
    """Parse a Pinterest board URL and return canonical form.

    Raises ValueError for invalid/unsupported URLs.
    """
    raw = url
    url = url.strip()

    if not url:
        raise ValueError("Empty URL provided")

    # Detect short links
    if re.match(r"https?://(www\.)?pin\.it/", url):
        raise ValueError("Short pin.it links are not supported (can't resolve without a browser)")

    # Normalize: add scheme if missing
    if url.startswith("/"):
        url = "https://www.pinterest.com" + url
    elif not url.startswith("http"):
        url = "https://" + url

    parsed = urlparse(url)

    # Validate host
    if parsed.hostname and not (
        parsed.hostname == "pinterest.com" or parsed.hostname.endswith(".pinterest.com")
    ):
        raise ValueError(f"Not a Pinterest URL: {raw}")

    path = parsed.path.strip("/")
    parts = [p for p in path.split("/") if p]

    # Reject pin URLs
    if "pin" in parts:
        raise ValueError(f"This looks like a single pin URL, not a board: {raw}")

    if len(parts) < 2:
        raise ValueError(f"Could not extract username and board name from: {raw}")

    username, boardname = parts[0], parts[1]

    # Reject reserved paths
    if username.lower() in ("pin", "search", "ideas", "today", "_", "settings"):
        raise ValueError(f"'{username}' is a reserved Pinterest path, not a username: {raw}")

    return {
        "canonical": f"https://www.pinterest.com/{username}/{boardname}/",
        "username": username,
        "boardname": boardname,
        "raw": raw,
    }
