"""
Menu page collection — httpx-first, Playwright fallback.

Strategy:
  1. httpx  — fast, no subprocess, handles HTTP/1.1 and HTTP/2 cleanly.
             Works for the majority of restaurant sites.
  2. Playwright — only used when httpx returns an empty/JS-gated page.
                  Handles SPAs that require JavaScript execution.

Both paths return plain-text page blobs ready for the LLM extractor.
"""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

_MENU_PATH_HINTS = {
    "/menu", "/food", "/order", "/eat", "/items", "/dining",
    "/allergen", "/nutrition", "/ingredient", "/dish",
}
_MENU_TEXT_HINTS = {"menu", "food", "order online", "allergen", "nutrition"}

_HTTPX_TIMEOUT  = 12.0
_MAX_MENU_PAGES = 3
_MAX_PAGE_CHARS = 6_000

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _strip_tags(html: str) -> str:
    """Remove HTML tags and collapse whitespace to plain text."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>",  " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _find_menu_links_in_html(html: str, base_url: str) -> list[str]:
    """Extract same-origin links that look like menu pages from raw HTML."""
    base_netloc = urlparse(base_url).netloc
    seen: set[str] = set()
    results: list[str] = []

    for href, text in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                                  html, flags=re.S | re.I):
        href = href.strip()
        if not href.startswith("http"):
            href = urljoin(base_url, href)

        if urlparse(href).netloc != base_netloc:
            continue

        path_lower = urlparse(href).path.lower()
        text_lower = re.sub(r"<[^>]+>", "", text).lower().strip()

        is_menu = (
            any(hint in path_lower for hint in _MENU_PATH_HINTS)
            or any(hint in text_lower for hint in _MENU_TEXT_HINTS)
        )

        if is_menu and href not in seen:
            seen.add(href)
            results.append(href)

    return results[:_MAX_MENU_PAGES]


def _looks_js_gated(text: str) -> bool:
    """Heuristic: page probably requires JS if visible text is very short."""
    return len(text) < 300


# ── httpx path ───────────────────────────────────────────────────────────────

async def _collect_with_httpx(website_url: str) -> list[str]:
    texts: list[str] = []
    try:
        async with httpx.AsyncClient(
            headers=_HEADERS,
            follow_redirects=True,
            timeout=_HTTPX_TIMEOUT,
            http2=False,           # force HTTP/1.1 — avoids protocol errors on many CDNs
        ) as client:
            # Fetch homepage
            try:
                resp = await client.get(website_url)
                resp.raise_for_status()
            except Exception as exc:
                logger.debug("[httpx] homepage failed for %s: %s", website_url, exc)
                return []

            homepage_html = resp.text
            homepage_text = _strip_tags(homepage_html)[:_MAX_PAGE_CHARS]

            menu_links = _find_menu_links_in_html(homepage_html, website_url)

            if not menu_links:
                if homepage_text:
                    texts.append(homepage_text)
                return texts

            for url in menu_links:
                try:
                    r = await client.get(url)
                    r.raise_for_status()
                    page_text = _strip_tags(r.text)[:_MAX_PAGE_CHARS]
                    if page_text:
                        texts.append(page_text)
                except Exception as exc:
                    logger.debug("[httpx] skipped %s: %s", url, exc)

    except Exception as exc:
        logger.warning("[httpx] collection failed for %s: %s", website_url, exc)

    return texts


# ── Playwright path (JS-gated sites) ─────────────────────────────────────────
#
# On Windows, uvicorn's SelectorEventLoop does not support subprocess creation.
# Playwright needs to spawn a Chromium process via asyncio subprocesses, which
# requires ProactorEventLoop.  The fix: run all Playwright work inside a
# dedicated thread that calls asyncio.run(), which creates a fresh
# ProactorEventLoop on Windows and a regular loop on Linux/Mac.

def _playwright_sync(website_url: str) -> list[str]:
    """
    Synchronous entry point that runs the async Playwright logic in a fresh
    event loop.  Called from a thread pool via run_in_executor.
    """
    import asyncio

    async def _inner() -> list[str]:
        texts: list[str] = []
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-extensions",
                        "--disable-background-networking",
                        "--disable-sync",
                        "--disable-translate",
                        "--no-first-run",
                    ],
                )
                try:
                    context = await browser.new_context(
                        user_agent=_HEADERS["User-Agent"],
                        java_script_enabled=True,
                        ignore_https_errors=True,
                    )
                    page = await context.new_page()
                    page.set_default_timeout(12_000)

                    try:
                        await page.goto(website_url, wait_until="domcontentloaded",
                                        timeout=12_000)
                        await page.wait_for_timeout(1_500)
                    except Exception as exc:
                        logger.debug("[playwright] goto failed for %s: %s", website_url, exc)
                        return []

                    homepage_html = await page.content()
                    menu_links = _find_menu_links_in_html(homepage_html, website_url)

                    async def _page_text() -> str:
                        try:
                            return (await page.inner_text("body"))[:_MAX_PAGE_CHARS]
                        except Exception:
                            return _strip_tags(await page.content())[:_MAX_PAGE_CHARS]

                    if not menu_links:
                        text = await _page_text()
                        if text:
                            texts.append(text)
                        return texts

                    for url in menu_links:
                        try:
                            await page.goto(url, wait_until="domcontentloaded",
                                            timeout=10_000)
                            await page.wait_for_timeout(1_000)
                            text = await _page_text()
                            if text:
                                texts.append(text)
                        except Exception as exc:
                            logger.debug("[playwright] skipped %s: %s", url, exc)

                finally:
                    await browser.close()

        except Exception as exc:
            logger.warning("[playwright] collection failed for %s: %s", website_url, exc)

        return texts

    # asyncio.run() creates a ProactorEventLoop on Windows, which supports
    # subprocess creation — solving the NotImplementedError.
    return asyncio.run(_inner())


async def _collect_with_playwright(website_url: str) -> list[str]:
    """
    Dispatch Playwright to a thread pool so the subprocess-capable event loop
    is isolated from uvicorn's SelectorEventLoop.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _playwright_sync, website_url)


# ── Public entry point ───────────────────────────────────────────────────────

async def collect_menu_pages(website_url: str) -> list[str]:
    """
    Collect menu page text from *website_url*.

    Tries httpx first (fast, reliable).  Falls back to Playwright if the
    page appears to be JS-gated (very little text returned).
    """
    texts = await _collect_with_httpx(website_url)

    if texts and not all(_looks_js_gated(t) for t in texts):
        logger.debug("[collector] httpx succeeded for %s (%d page(s))", website_url, len(texts))
        return texts

    logger.debug("[collector] httpx returned thin content for %s — trying Playwright", website_url)
    pw_texts = await _collect_with_playwright(website_url)
    return pw_texts if pw_texts else texts  # return whatever we have
