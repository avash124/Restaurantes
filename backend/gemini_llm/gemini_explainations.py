from google.genai import types
from pydantic import BaseModel
from backend.gemini_llm.gemini_client import get_gemini_client
from backend.gemini_llm.gemini_prompts import build_short_explanation_prompt


class ShortExplanation(BaseModel):
    short_explanation: str


def generate_short_explanation_with_gemini(
    item_name: str,
    label: str,
    confidence_band: str,
    reasons: list[str],
    missing_info: list[str],
    ingredients: list[str] | None = None,
    condition_ids: list[str] | None = None,
) -> str:
    client = get_gemini_client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_short_explanation_prompt(
            item_name, label, confidence_band, reasons, missing_info,
            ingredients=ingredients,
            condition_ids=condition_ids,
        ),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ShortExplanation,
        ),
    )

    if response.parsed is None:
        raise ValueError(f"Gemini returned no structured output for item: {item_name}")

    return response.parsed.short_explanation


async def generate_short_explanation_with_gemini_async(
    item_name: str,
    label: str,
    confidence_band: str,
    reasons: list[str],
    missing_info: list[str],
    ingredients: list[str] | None = None,
    condition_ids: list[str] | None = None,
) -> str:
    client = get_gemini_client()

    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_short_explanation_prompt(
            item_name, label, confidence_band, reasons, missing_info,
            ingredients=ingredients,
            condition_ids=condition_ids,
        ),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ShortExplanation,
        ),
    )

    if response.parsed is None:
        raise ValueError(f"Gemini returned no structured output for item: {item_name}")

    return response.parsed.short_explanation