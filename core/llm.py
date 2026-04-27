import math
import re
import random
from typing import Optional, List

from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from langchain_groq import ChatGroq
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
        # Fallback to the first key in the rotation list if available during boot
        keys = _get_gemini_keys()
        if settings.ENABLE_KEY_ROTATION and keys:
            return keys[0]
            
        raise LLMServiceError(
            "LLM provider is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY.",
            status_code=503,
        )
    return api_key



def _groq_api_key() -> str:
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise LLMServiceError(
            "Groq is not configured. Set GROQ_API_KEY.",
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


def get_groq_llm(temperature: float = 0.2) -> ChatGroq:
    return ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=_groq_api_key(),
        temperature=temperature,
    )


# Primary shared chatbot model: Gemini via Google's OpenAI-compatible endpoint.
gemini_llm = get_llm(temperature=0.2)

# Secondary provider used as an automatic fallback when Gemini is unavailable.
groq_llm = get_groq_llm(temperature=0.2)


async def _invoke_with_provider(provider_name: str, llm, prompt: str):
    try:
        response = await llm.ainvoke(prompt)
        return response.content
    except RateLimitError as exc:
        message = str(exc)
        raise LLMServiceError(
            f"{provider_name} is temporarily rate limited. Please retry in about a minute.",
            status_code=429,
            retry_after=_extract_retry_after_seconds(message),
        ) from exc
    except (APITimeoutError, APIConnectionError) as exc:
        raise LLMServiceError(
            f"{provider_name} is temporarily unavailable. Please retry shortly.",
            status_code=503,
        ) from exc
    except APIStatusError as exc:
        raise LLMServiceError(
            f"{provider_name} returned an upstream error ({exc.status_code}). Please retry shortly.",
            status_code=503,
        ) from exc


def _get_gemini_keys() -> List[str]:
    if not settings.GEMINI_API_KEYS:
        return []
    return [k.strip() for k in settings.GEMINI_API_KEYS.split(",") if k.strip()]


async def call_llm(prompt: str):
    """
    Generic helper for all LangGraph agents with dynamic key rotation support.
    """
    keys = _get_gemini_keys()
    
    if settings.ENABLE_KEY_ROTATION and keys:
        # Randomize to distribute load across keys
        shuffled_keys = list(keys)
        random.shuffle(shuffled_keys)
        
        last_error = None
        for i, key in enumerate(shuffled_keys):
            try:
                # Temporary LLM instance for this specific key
                llm = ChatOpenAI(
                    model=settings.GEMINI_MODEL,
                    api_key=key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    temperature=0.2,
                )
                return await _invoke_with_provider(f"Gemini (Key {i+1})", llm, prompt)
            except LLMServiceError as e:
                if e.status_code in {429, 503}:
                    last_error = e
                    continue # Try next key
                raise # Critical error
        
        # If all keys failed, we still have the primary Gemini and Groq fallbacks below
        if last_error:
            print(f"All {len(shuffled_keys)} keys in rotation failed. Falling back to primary LLMs.")

    # Primary shared chatbot model: Gemini
    try:
        return await _invoke_with_provider("Gemini (Primary)", gemini_llm, prompt)
    except LLMServiceError as gemini_error:
        if gemini_error.status_code not in {429, 503}:
            raise

        # Secondary provider fallback: Groq
        try:
            return await _invoke_with_provider("Groq", groq_llm, prompt)
        except LLMServiceError as groq_error:
            if gemini_error.status_code == 429:
                raise LLMServiceError(
                    "Gemini is rate limited and Groq fallback is unavailable. Please retry shortly.",
                    status_code=groq_error.status_code,
                    retry_after=gemini_error.retry_after or groq_error.retry_after,
                ) from groq_error
            raise groq_error
