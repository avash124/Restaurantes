from functools import lru_cache
from google import genai
import os


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_GEMINI_API_KEY environment variable is not set")
    return genai.Client(api_key=api_key)