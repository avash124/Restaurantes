"""
Wide restaurant discovery via Gemini + Google Search grounding.

Replaces the old browser-use session approach (which timed out at 90 s) with a
direct Gemini call that uses the built-in Google Search tool.  Typical latency
is 3-8 seconds instead of 90+.
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import re

from google.genai import types

from backend.gemini_llm.gemini_client import get_gemini_client
from backend.browser_use.agents.structured_schemas import (
    WideDiscoveryOutput,
    WideRestaurantRecord,
)

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.5-flash"

_PROMPT_TEMPLATE = """\
Search for restaurants near {location} (within {radius_miles} miles) \
that match the category "{category}".

Return a JSON object with a single key "restaurants" whose value is an array \
of up to 15 objects.  Each object must have exactly these fields:
  name            (string)
  address         (string — full street address)
  website_url     (string or null)
  cuisine         (string or null)
  discovery_confidence  (float 0.0–1.0 — how well it matches the category)

Output ONLY valid JSON, no markdown fences, no extra text.
"""


def _extract_json(text: str) -> dict:
    """
    Pull the first balanced {...} block out of a model response.

    Uses brace-depth tracking (respecting quoted strings and escape sequences)
    instead of rfind('}'), which would break when Gemini appends trailing
    commentary after the JSON object.
    """
    # Strip markdown fences if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response")

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
                candidate = text[start : i + 1]
                return json.loads(candidate)

    raise ValueError("No complete JSON object found in model response")


def _call_wide_gemini(client, prompt: str):
    """Synchronous Gemini call — run via run_in_executor to avoid blocking the event loop."""
    return client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.0,
        ),
    )


async def run_wide_discovery_agent(
    location: str,
    radius_miles: float,
    category: str,
) -> WideDiscoveryOutput:
    try:
        client = get_gemini_client()
    except Exception as exc:
        logger.warning("[wide] Gemini client unavailable: %s", exc)
        return WideDiscoveryOutput(restaurants=[])

    prompt = _PROMPT_TEMPLATE.format(
        location=location,
        radius_miles=radius_miles,
        category=category,
    )

    # Run the synchronous Gemini SDK call in a thread so the event loop (and
    # Redis async operations) are not blocked during the 3-8 second API call.
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None, functools.partial(_call_wide_gemini, client, prompt)
        )
    except Exception as exc:
        logger.warning("[wide] Gemini generate_content failed: %s", exc)
        return WideDiscoveryOutput(restaurants=[])

    raw_text = (response.text or "").strip()
    if not raw_text:
        logger.warning("[wide] Gemini returned empty response for %s / %s", location, category)
        return WideDiscoveryOutput(restaurants=[])

    try:
        data = _extract_json(raw_text)
        return WideDiscoveryOutput.model_validate(data)
    except Exception as exc:
        logger.warning("[wide] Failed to parse Gemini response: %s\nRaw: %.300s", exc, raw_text)
        # Best-effort: try to salvage a list if the model returned one directly
        try:
            lst = json.loads(raw_text) if raw_text.startswith("[") else []
            if isinstance(lst, list):
                records = [WideRestaurantRecord.model_validate(r) for r in lst]
                return WideDiscoveryOutput(restaurants=records)
        except Exception:
            pass
        return WideDiscoveryOutput(restaurants=[])
