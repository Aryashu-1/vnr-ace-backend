import math
import re
from typing import Optional

from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from langchain_openai import ChatOpenAI
from core.config import settings


class LLMServiceError(Exception):
    """Raised when the upstream LLM provider cannot serve the request cleanly."""

    def __init__(
        self,
        detail: str,
        *,
        status_code: int = 503,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.retry_after = retry_after


def _gemini_api_key() -> str:
    api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
    if not api_key:
        raise LLMServiceError(
            "LLM provider is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY.",
            status_code=503,
        )
    return api_key


def _extract_retry_after_seconds(message: str) -> Optional[int]:
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", message, flags=re.IGNORECASE)
    if not match:
        return None
    return max(1, math.ceil(float(match.group(1))))


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


# Primary shared chatbot model: Gemini via Google's OpenAI-compatible endpoint.
gemini_llm = get_llm(temperature=0.2)

# Keep legacy name for compatibility across the codebase.
groq_llm = gemini_llm


async def call_llm(prompt: str):
    """
    Generic helper for all LangGraph agents.
    """
    try:
        response = await gemini_llm.ainvoke(prompt)
        return response.content
    except RateLimitError as exc:
        message = str(exc)
        raise LLMServiceError(
            "The AI provider is temporarily rate limited. Please retry in about a minute.",
            status_code=429,
            retry_after=_extract_retry_after_seconds(message),
        ) from exc
    except (APITimeoutError, APIConnectionError) as exc:
        raise LLMServiceError(
            "The AI provider is temporarily unavailable. Please retry shortly.",
            status_code=503,
        ) from exc
    except APIStatusError as exc:
        raise LLMServiceError(
            f"The AI provider returned an upstream error ({exc.status_code}). Please retry shortly.",
            status_code=503,
        ) from exc
