"""Playwright-based Pinterest board scraper with infinite scroll."""

import asyncio
import logging

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


async def scrape_board(canonical_url: str, limit: int | None = None) -> list[dict]:
    """Scrape pins from a Pinterest board URL."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(canonical_url, wait_until="domcontentloaded", timeout=30000)

            # Dismiss cookie consent
            for selector in [
                "button:has-text('Accept')", "button:has-text('accepteer')",
                "button:has-text('I agree')", "button:has-text('Akkoord')",
                "button:has-text('Continue')",
            ]:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        break
                except PlaywrightError as e:
                    logger.debug("Cookie consent selector %s not found: %s", selector, e)
                    continue

            await asyncio.sleep(2)

            # Scroll and collect
            no_new_count = 0
            seen_ids: set[str] = set()
            pins: list[dict] = []

            while no_new_count < 3:
                if limit is not None and len(pins) >= limit:
                    break

                await page.evaluate("window.scrollBy(0, 2000)")
                await asyncio.sleep(1.5)

                # Try multiple selectors for pin elements
                elements = await page.query_selector_all("[data-test-id='pin']")
                if not elements:
                    elements = await page.query_selector_all("[data-pin-id]")

                new_found = 0
                for el in elements:
                    pin_id = await el.get_attribute("data-pin-id") or ""
                    if not pin_id:
                        # Try to extract from a link
                        link_el = await el.query_selector("a[href*='/pin/']")
                        if link_el:
                            href = await link_el.get_attribute("href") or ""
                            parts = [p for p in href.split("/") if p]
                            idx = parts.index("pin") if "pin" in parts else -1
                            if idx >= 0 and idx + 1 < len(parts):
                                pin_id = parts[idx + 1]

                    if not pin_id or pin_id in seen_ids:
                        continue

                    seen_ids.add(pin_id)
                    new_found += 1

                    # Extract image
                    image_url = ""
                    img = await el.query_selector("img")
                    if img:
                        srcset = await img.get_attribute("srcset") or ""
                        if srcset:
                            # Pick highest resolution by parsing width descriptors (e.g. "750w")
                            best_url = ""
                            best_w = -1
                            for part in srcset.split(","):
                                tokens = part.strip().split()
                                if not tokens:
                                    continue
                                url_candidate = tokens[0]
                                w = 0
                                if len(tokens) > 1:
                                    desc = tokens[1].lower()
                                    if desc.endswith("w"):
                                        try:
                                            w = int(desc[:-1])
                                        except ValueError:
                                            pass
                                if w > best_w:
                                    best_w = w
                                    best_url = url_candidate
                            image_url = best_url
                        if not image_url:
                            image_url = await img.get_attribute("src") or ""

                    # Extract title/alt
                    title = ""
                    if img:
                        title = await img.get_attribute("alt") or ""

                    # Extract link
                    link = ""
                    link_el = await el.query_selector("a[href*='/pin/']")
                    if link_el:
                        link = await link_el.get_attribute("href") or ""
                        if link.startswith("/"):
                            link = "https://www.pinterest.com" + link

                    pins.append({
                        "id": pin_id,
                        "image_url": image_url,
                        "title": title,
                        "description": "",
                        "link": link,
                        "board_url": canonical_url,
                    })

                    if limit is not None and len(pins) >= limit:
                        break

                no_new_count = 0 if new_found > 0 else no_new_count + 1

        finally:
            await browser.close()

    return pins


def scrape_board_sync(canonical_url: str, limit: int | None = None) -> list[dict]:
    """Synchronous wrapper for scrape_board."""
    return asyncio.run(scrape_board(canonical_url, limit))
