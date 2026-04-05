from backend.gemini_llm.gemini_client import get_gemini_client


def embed_text(text: str) -> list[float]:
    client = get_gemini_client()

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )

    if not response.embeddings:
        raise ValueError("Gemini returned no embeddings for the provided text")

    return response.embeddings[0].values