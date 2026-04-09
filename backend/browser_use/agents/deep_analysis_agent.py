"""
Deep restaurant analysis agent.

Priority order for each restaurant:
  1. Playwright + Gemini (fast, deterministic — used when website_url is known)
  2. Gemini + Google Search grounding (fallback when Playwright yields
     too few items or no website URL is available)

Both paths use the same LLM extractor / schema.
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import re

from google.genai import types

from backend.browser_use.agents.structured_schemas import DeepRestaurantOutput
from backend.browser_use.agents.playwright_collector import _collect_with_httpx
from backend.browser_use.agents.llm_extractor import extract_menu_from_pages
from backend.gemini_llm.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.5-flash"
_MIN_ITEMS_THRESHOLD = 1

_SEARCH_PROMPT = """\
Search for the menu of the restaurant "{restaurant_name}"{location_clause}.

List every menu item you can find. Include for each item:
- its name and category
- a brief description
- any ingredients stated on the menu
- any allergens stated on the menu
- any dietary/preparation tags (e.g. vegan, gluten-free, grilled)

Return plain text only — do NOT return JSON. Just list the items naturally.
"""

_EXTRACT_PROMPT = """\
Convert the following restaurant menu information into structured JSON.

Restaurant name: {restaurant_name}

Menu information:
{menu_text}

Return a JSON object matching this schema exactly (no markdown fences, no extra text):
{{
  "restaurant_name": "{restaurant_name}",
  "address": "<address if present, else empty string>",
  "website_url": null,
  "menu_items": [
    {{
      "name": "string",
      "category": "string or null",
      "description": "string or null",
      "ingredients_explicit": [],
      "ingredients_inferred": [],
      "allergens_explicit": [],
      "preparation_tags": [],
      "uncertainty_flags": [],
      "nutrition_explicit": {{}},
      "sourcing_notes": [],
      "evidence_source_type": "restaurant_explicit",
      "extraction_confidence": 0.7
    }}
  ]
}}
"""


def _extract_json(text: str) -> dict:
    """
    Pull the first balanced {...} block out of a model response.

    Uses brace-depth tracking (respecting quoted strings and escape sequences)
    so trailing commentary added by Gemini after the JSON object does not break
    the parser (unlike the old rfind('}') approach).
    """
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object in model response")

    depth = 0
    in_string = False
    escape_next = False

    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])

    raise ValueError("No complete JSON object found in model response")


async def _gemini_search_fallback(
    restaurant_name: str,
    website_url: str | None,
    location_hint: str | None,
) -> DeepRestaurantOutput:
    """
    Two-call approach that avoids the 'Server disconnected' error:

    Call 1 — google_search grounding, plain-text output.
              Asking for JSON + grounding in one call causes the API to drop
              the connection; plain text avoids that.

    Call 2 — no tools, JSON response mode.
              Parses the plain-text menu into the structured schema.

    Both Gemini calls are run in a thread executor so the asyncio event loop
    (and Redis async operations) are never blocked.
    """
    try:
        client = get_gemini_client()
    except Exception as exc:
        logger.warning("[deep] Gemini client unavailable: %s", exc)
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name, address="",
            website_url=website_url, menu_items=[],
        )

    location_clause = f" located in {location_hint}" if location_hint else ""
    search_prompt = _SEARCH_PROMPT.format(
        restaurant_name=restaurant_name,
        location_clause=location_clause,
    )
    if website_url:
        search_prompt = f"The restaurant's website is {website_url}.\n\n" + search_prompt

    # ── Call 1: search for menu (plain text, grounding enabled) ──────────────
    def _do_search():
        return client.models.generate_content(
            model=_MODEL,
            contents=search_prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )

    loop = asyncio.get_running_loop()
    try:
        search_resp = await loop.run_in_executor(None, _do_search)
    except Exception as exc:
        logger.warning("[deep] Gemini search call failed for %s: %s", restaurant_name, exc)
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name, address="",
            website_url=website_url, menu_items=[],
        )

    menu_text = (search_resp.text or "").strip()
    if not menu_text:
        logger.warning("[deep] Gemini search returned empty text for %s", restaurant_name)
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name, address="",
            website_url=website_url, menu_items=[],
        )

    logger.debug("[deep] search returned %d chars for %s", len(menu_text), restaurant_name)

    # ── Call 2: extract JSON (no tools, JSON mode) ────────────────────────────
    # Escape any curly braces in the dynamic parts before calling .format() so
    # that content returned by Gemini cannot inadvertently break the template.
    safe_name = restaurant_name.replace("{", "{{").replace("}", "}}")
    safe_menu = menu_text[:8_000].replace("{", "{{").replace("}", "}}")
    try:
        extract_prompt = _EXTRACT_PROMPT.format(
            restaurant_name=safe_name,
            menu_text=safe_menu,
        )
    except Exception as exc:
        logger.warning("[deep] prompt formatting failed for %s: %s", restaurant_name, exc)
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name, address="",
            website_url=website_url, menu_items=[],
        )

    def _do_extract():
        return client.models.generate_content(
            model=_MODEL,
            contents=extract_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )

    try:
        extract_resp = await loop.run_in_executor(None, _do_extract)
    except Exception as exc:
        logger.warning("[deep] Gemini extract call failed for %s: %s", restaurant_name, exc)
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name, address="",
            website_url=website_url, menu_items=[],
        )

    raw = (extract_resp.text or "").strip()
    if not raw:
        logger.warning("[deep] Gemini extract returned empty JSON for %s", restaurant_name)
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name, address="",
            website_url=website_url, menu_items=[],
        )

    try:
        data = _extract_json(raw)
    except Exception as exc:
        logger.warning("[deep] JSON parse failed for %s: %s\nRaw: %.300s", restaurant_name, exc, raw)
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name, address="",
            website_url=website_url, menu_items=[],
        )

    data.setdefault("restaurant_name", restaurant_name)
    data.setdefault("address", "")
    data.setdefault("website_url", website_url)
    data.setdefault("menu_items", [])

    try:
        return DeepRestaurantOutput.model_validate(data)
    except Exception as exc:
        logger.warning("[deep] schema validation failed for %s: %s", restaurant_name, exc)
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name, address="",
            website_url=website_url, menu_items=[],
        )


async def run_deep_restaurant_agent(
    restaurant_name: str,
    website_url: str | None = None,
    location_hint: str | None = None,
) -> DeepRestaurantOutput:
    """
    Analyse a restaurant and return structured menu data.

    Fast path  : Playwright page collection → Gemini Flash extraction.
    Fallback   : Gemini + Google Search grounding (no browser-use sessions).
    """
    # ── Fast path: httpx + LLM (no browser startup overhead) ────────────────
    # Playwright is skipped intentionally: browser launch adds 2-5s even when
    # the site is JS-gated and falls back anyway.  httpx either gets readable
    # HTML quickly or times out in 6s, then we use Gemini search as fallback.
    if website_url:
        try:
            logger.debug("[deep] trying httpx fast path for %s", restaurant_name)
            page_texts = await _collect_with_httpx(website_url)

            if page_texts:
                result = await extract_menu_from_pages(
                    restaurant_name=restaurant_name,
                    address="",
                    website_url=website_url,
                    page_texts=page_texts,
                )
                if len(result.menu_items) >= _MIN_ITEMS_THRESHOLD:
                    logger.debug(
                        "[deep] httpx fast path succeeded for %s (%d items)",
                        restaurant_name, len(result.menu_items),
                    )
                    return result
                else:
                    logger.debug(
                        "[deep] httpx returned %d items for %s — falling back to Gemini search",
                        len(result.menu_items), restaurant_name,
                    )
        except Exception as exc:
            logger.warning("[deep] httpx fast path error for %s: %s", restaurant_name, exc)

    # ── Fallback: Gemini + Google Search ─────────────────────────────────────
    logger.debug("[deep] using Gemini search fallback for %s", restaurant_name)
    return await _gemini_search_fallback(restaurant_name, website_url, location_hint)
