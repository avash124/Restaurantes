"""
Parses a user's chat message to extract a clean search intent:
- cuisine types (e.g. ["Mexican", "Italian"]) or empty list for "any"
- free-form query terms the user mentioned

Returns a single `category` string suitable for the browser-use discovery agent.
Falls back to "restaurant" on any error so the pipeline never stalls.
"""

from __future__ import annotations

import json
import logging

from backend.gemini_llm.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a search-intent parser. Given a user message, extract the type of "
    "restaurant or cuisine they want. Return ONLY a JSON object with two keys:\n"
    "  cuisine_types: list[str]  — specific cuisines mentioned (e.g. [\"Mexican\", \"Thai\"]). "
    "Empty list if the user did not specify.\n"
    "  extra_terms: list[str]   — other relevant search terms (e.g. [\"fast food\", \"buffet\", "
    "\"vegetarian-friendly\"]). Empty list if none.\n"
    "Do NOT include health conditions or allergies — those are handled separately.\n"
    "Examples:\n"
    "  'I want tacos' -> {\"cuisine_types\": [\"Mexican\"], \"extra_terms\": []}\n"
    "  'Find me a nice Italian or Greek place' -> {\"cuisine_types\": [\"Italian\", \"Greek\"], \"extra_terms\": []}\n"
    "  'Somewhere to eat' -> {\"cuisine_types\": [], \"extra_terms\": []}\n"
    "  'cheap sushi buffet' -> {\"cuisine_types\": [\"Japanese\", \"Sushi\"], \"extra_terms\": [\"buffet\", \"cheap\"]}\n"
)


async def parse_search_intent(user_message: str) -> str:
    """
    Returns a category string like "Mexican, Tex-Mex" or "restaurant" to pass
    to the wide-discovery browser agent.
    """
    if not user_message.strip():
        return "restaurant"

    try:
        client = get_gemini_client()

        response = await _run_in_thread(client, user_message)

        raw = response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)
        cuisine_types: list[str] = data.get("cuisine_types") or []
        extra_terms: list[str] = data.get("extra_terms") or []

        parts = [t for t in cuisine_types + extra_terms if t and isinstance(t, str)]
        if parts:
            return ", ".join(parts)

    except Exception as exc:
        logger.warning("[intent_parser] failed to parse intent: %s", exc)

    return "restaurant"


async def _run_in_thread(client, user_message: str):
    """Run the synchronous Gemini call in a thread so we don't block the event loop."""
    import asyncio
    import functools

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        functools.partial(_call_gemini, client, user_message),
    )


def _call_gemini(client, user_message: str):
    from google.genai import types as genai_types

    return client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_message,
        config=genai_types.GenerateContentConfig(
            system_instruction=_SYSTEM,
            temperature=0.0,
            max_output_tokens=128,
        ),
    )
