"""
Deep restaurant analysis agent.

Priority order for each restaurant:
  1. Playwright + Gemini (fast, deterministic — used when website_url is known)
  2. Two short browser-use follow-up sessions (fallback when Playwright yields
     too few items or no website URL is available):
       Session 1 — find the menu URL
       Session 2 — extract items from that URL

This keeps browser-use sessions short and focused, reducing end-to-end latency.
"""

from __future__ import annotations

import asyncio
import json
import logging

from backend.browser_use.agents.browser_use_client import get_browseruse_client
from backend.browser_use.agents.structured_schemas import DeepRestaurantOutput
from backend.browser_use.agents.playwright_collector import collect_menu_pages
from backend.browser_use.agents.llm_extractor import extract_menu_from_pages
from backend.browser_use import session_registry

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {"finished", "failed", "stopped"}
_POLL_INTERVAL = 2.0
_POLL_TIMEOUT_SECONDS = 90.0

# Only fall back to browser-use when Playwright+LLM finds zero items.
_MIN_ITEMS_THRESHOLD = 1


# ── Helper: run a single browser-use session to completion ──────────────────

async def _run_session(task: str, output_schema: dict) -> dict | None:
    """
    Create and poll one browser-use session.  Returns the raw output dict on
    success, or None if the session errors / returns nothing.
    All exceptions (including missing API key) are caught here so they never
    propagate as unretrieved task exceptions in asyncio.gather callers.
    """
    try:
        client = get_browseruse_client()
    except Exception as exc:
        logger.warning("[deep] browser-use client unavailable: %s", exc)
        return None

    task_id: str | None = None
    task_result = None
    try:
        task_resp = await client.tasks.create(task, structured_output=json.dumps(output_schema))
        task_id = str(task_resp.id)
        session_registry.register(task_id)

        try:
            async with asyncio.timeout(_POLL_TIMEOUT_SECONDS):
                while True:
                    task_result = await client.tasks.get(task_id)
                    if task_result.status.value in _TERMINAL_STATUSES:
                        break
                    await asyncio.sleep(_POLL_INTERVAL)
        except TimeoutError:
            logger.warning("[deep] task %s timed out after %.1fs", task_id, _POLL_TIMEOUT_SECONDS)
            try:
                await client.tasks.stop(task_id)
            except Exception as stop_exc:
                logger.debug("[deep] could not stop timed out task %s: %s", task_id, stop_exc)
            return None

        if task_result is None or task_result.output is None:
            logger.warning("[deep] task %s finished with no output", task_id)
            return None

        output = task_result.output
        if isinstance(output, str):
            output = json.loads(output)
        return output

    except Exception as exc:
        logger.warning("[deep] task error: %s", exc)
        return None

    finally:
        if task_id:
            session_registry.unregister(task_id)


# ── Follow-up session pair ───────────────────────────────────────────────────

async def _browser_use_two_sessions(
    restaurant_name: str,
    website_url: str | None,
    location_hint: str | None,
) -> DeepRestaurantOutput:
    """
    Two short, focused browser-use sessions:
      Session 1 — discover the menu URL (if not already known)
      Session 2 — extract menu items from that URL
    """
    from pydantic import BaseModel

    class MenuUrlResult(BaseModel):
        menu_url: str | None = None

    # ── Session 1: find menu URL ─────────────────────────────────────────────
    if website_url:
        find_task = (
            f'Go to "{website_url}" and return the direct URL of the menu or '
            "food page (e.g. /menu, /food, /order). "
            "Return ONLY the URL, nothing else. "
            "Do NOT read or summarise the menu content."
        )
    else:
        find_task = (
            f'Search for the official website of "{restaurant_name}"'
            + (f" in {location_hint}" if location_hint else "")
            + ". Return the direct URL of its menu or food page. "
            "Do NOT read or summarise the menu content."
        )

    url_schema = MenuUrlResult.model_json_schema()
    url_output = await _run_session(find_task, url_schema)
    menu_url: str | None = None

    if url_output and isinstance(url_output, dict):
        menu_url = url_output.get("menu_url") or website_url
    else:
        menu_url = website_url

    if not menu_url:
        logger.warning("[deep] could not find menu URL for %s", restaurant_name)
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name,
            address="",
            website_url=website_url,
            menu_items=[],
        )

    # ── Session 2: extract menu items ────────────────────────────────────────
    extract_task = (
        f'Visit "{menu_url}" (the menu page for "{restaurant_name}"). '
        "Extract every menu item visible. "
        "For each item return: name, category, description, "
        "ingredients_explicit, allergens_explicit, preparation_tags, "
        "and extraction_confidence. "
        "Do NOT navigate to other pages."
    )

    extract_schema = DeepRestaurantOutput.model_json_schema()
    extract_output = await _run_session(extract_task, extract_schema)

    if extract_output is None:
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name,
            address="",
            website_url=website_url,
            menu_items=[],
        )

    extract_output.setdefault("restaurant_name", restaurant_name)
    extract_output.setdefault("address", "")
    extract_output.setdefault("website_url", website_url or menu_url)

    try:
        return DeepRestaurantOutput.model_validate(extract_output)
    except Exception as exc:
        logger.warning("[deep] schema validation failed for %s: %s", restaurant_name, exc)
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name,
            address="",
            website_url=website_url,
            menu_items=[],
        )


# ── Public entry point ───────────────────────────────────────────────────────

async def run_deep_restaurant_agent(
    restaurant_name: str,
    website_url: str | None = None,
    location_hint: str | None = None,
) -> DeepRestaurantOutput:
    """
    Analyse a restaurant and return structured menu data.

    Fast path  : Playwright page collection → Gemini Flash extraction.
    Fallback   : Two short browser-use sessions (find URL → extract items).
    """
    # ── Fast path: Playwright + LLM ──────────────────────────────────────────
    if website_url:
        try:
            logger.debug("[deep] trying Playwright fast path for %s", restaurant_name)
            page_texts = await collect_menu_pages(website_url)

            if page_texts:
                result = await extract_menu_from_pages(
                    restaurant_name=restaurant_name,
                    address="",
                    website_url=website_url,
                    page_texts=page_texts,
                )
                if len(result.menu_items) >= _MIN_ITEMS_THRESHOLD:
                    logger.debug(
                        "[deep] Playwright fast path succeeded for %s (%d items)",
                        restaurant_name, len(result.menu_items),
                    )
                    return result
                else:
                    logger.debug(
                        "[deep] Playwright returned %d items for %s — falling back to browser-use",
                        len(result.menu_items), restaurant_name,
                    )
        except Exception as exc:
            logger.warning("[deep] Playwright fast path error for %s: %s", restaurant_name, exc)

    # ── Fallback: two focused browser-use sessions ───────────────────────────
    logger.debug("[deep] using browser-use sessions for %s", restaurant_name)
    return await _browser_use_two_sessions(restaurant_name, website_url, location_hint)
