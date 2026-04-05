"""
LLM-based menu extraction.

Takes raw page text collected by the Playwright collector and uses Gemini Flash
to parse it into structured DeepRestaurantOutput.  This separates page
collection (Playwright, deterministic) from data extraction (LLM, flexible).
"""

from __future__ import annotations

import asyncio
import json
import logging
from functools import partial

from backend.browser_use.agents.structured_schemas import DeepRestaurantOutput
from backend.gemini_llm.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)

_MAX_INPUT_CHARS = 14_000   # ~3.5k tokens — fast for Flash
_MODEL = "gemini-2.5-flash"

_SYSTEM = (
    "You are a precise menu-data extractor. "
    "Given raw restaurant-page text, extract every menu item you can identify. "
    "Return ONLY valid JSON — no markdown, no explanation."
)

_SCHEMA_HINT = """{
  "restaurant_name": "string",
  "address": "string",
  "website_url": "string | null",
  "menu_items": [
    {
      "name": "string",
      "category": "string | null",
      "description": "string | null",
      "ingredients_explicit": ["string"],
      "ingredients_inferred": ["string"],
      "allergens_explicit": ["string"],
      "preparation_tags": ["string"],
      "uncertainty_flags": ["string"],
      "nutrition_explicit": {},
      "sourcing_notes": ["string"],
      "evidence_source_type": "restaurant_explicit",
      "extraction_confidence": 0.0
    }
  ]
}"""


def _build_prompt(restaurant_name: str, address: str, website_url: str | None, page_texts: list[str]) -> str:
    combined = "\n\n--- page break ---\n\n".join(page_texts)[:_MAX_INPUT_CHARS]
    url_line = f"Website: {website_url}" if website_url else ""
    return (
        f"Restaurant: {restaurant_name}\n"
        f"Address: {address}\n"
        f"{url_line}\n\n"
        "Page content:\n"
        f"{combined}\n\n"
        "Extract all menu items and return JSON matching this schema exactly:\n"
        f"{_SCHEMA_HINT}\n\n"
        'If no menu items are found return an empty "menu_items" list. '
        "Set extraction_confidence between 0.0 and 1.0 per item."
    )


def _call_gemini(prompt: str) -> str:
    client = get_gemini_client()
    response = client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    return response.text or "{}"


async def extract_menu_from_pages(
    restaurant_name: str,
    address: str,
    website_url: str | None,
    page_texts: list[str],
) -> DeepRestaurantOutput:
    """
    Call Gemini Flash in a thread pool (non-blocking) to extract menu items
    from *page_texts* collected by the Playwright collector.
    """
    if not page_texts:
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name,
            address=address,
            website_url=website_url,
            menu_items=[],
        )

    prompt = _build_prompt(restaurant_name, address, website_url, page_texts)

    loop = asyncio.get_running_loop()
    try:
        raw = await loop.run_in_executor(None, partial(_call_gemini, prompt))
    except Exception as exc:
        logger.warning("[llm_extractor] Gemini call failed for %s: %s", restaurant_name, exc)
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name,
            address=address,
            website_url=website_url,
            menu_items=[],
        )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("[llm_extractor] JSON parse failed for %s", restaurant_name)
        data = {}

    # Ensure required top-level fields are present before validation.
    data.setdefault("restaurant_name", restaurant_name)
    data.setdefault("address", address)
    data.setdefault("website_url", website_url)
    data.setdefault("menu_items", [])

    try:
        return DeepRestaurantOutput.model_validate(data)
    except Exception as exc:
        logger.warning("[llm_extractor] schema validation failed for %s: %s", restaurant_name, exc)
        return DeepRestaurantOutput(
            restaurant_name=restaurant_name,
            address=address,
            website_url=website_url,
            menu_items=[],
        )
