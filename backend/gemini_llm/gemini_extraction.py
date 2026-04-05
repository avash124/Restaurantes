from google.genai import types
from backend.gemini_llm.gemini_client import get_gemini_client
from backend.gemini_llm.gemini_prompts import build_extraction_prompt
from backend.browser_use.agents.structured_schemas import DeepRestaurantOutput


def extract_restaurant_structured(page_bundle_text: str) -> DeepRestaurantOutput:
    client = get_gemini_client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_extraction_prompt(page_bundle_text),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DeepRestaurantOutput,
        ),
    )

    if response.parsed is None:
        raise ValueError("Gemini returned no structured output for extraction")

    return response.parsed