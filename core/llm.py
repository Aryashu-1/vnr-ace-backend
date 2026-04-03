# core/llm.py

from langchain_openai import ChatOpenAI
from core.config import settings


def _gemini_api_key() -> str:
    api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
    if not api_key:
        raise ValueError("Missing Gemini API key. Set GEMINI_API_KEY (or GOOGLE_API_KEY).")
    return api_key


def get_llm(temperature: float = 0.2) -> ChatOpenAI:
    """
    Gemini via Google's OpenAI-compatible endpoint.
    """
    return ChatOpenAI(
        model=settings.GEMINI_MODEL,
        api_key=_gemini_api_key(),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        temperature=temperature,
    )


# Keep legacy name for compatibility across the codebase.
groq_llm = get_llm(temperature=0.2)


async def call_llm(prompt: str):
    """
    Generic helper for all LangGraph agents.
    """
    response = groq_llm.invoke(prompt)
    return response.content
