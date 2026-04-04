import asyncio
import sys
from pathlib import Path

import httpx
from openai import RateLimitError
from langchain_groq import ChatGroq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import llm


def _rate_limit_error() -> RateLimitError:
    request = httpx.Request("POST", "https://example.test/chat/completions")
    response = httpx.Response(status_code=429, request=request)
    return RateLimitError(
        "quota exceeded, please retry in 54.2s",
        response=response,
        body=None,
    )


def test_call_llm_wraps_rate_limit_error(monkeypatch):
    async def fake_gemini_ainvoke(self, prompt: str):
        raise _rate_limit_error()

    async def fake_groq_ainvoke(self, prompt: str):
        return type("Resp", (), {"content": "groq fallback"})()

    monkeypatch.setattr(llm.gemini_llm.__class__, "ainvoke", fake_gemini_ainvoke)
    monkeypatch.setattr(ChatGroq, "ainvoke", fake_groq_ainvoke)

    async def run():
        response = await llm.call_llm("hello")
        assert response == "groq fallback"

    asyncio.run(run())


def test_call_llm_raises_when_both_providers_fail(monkeypatch):
    async def fake_gemini_ainvoke(self, prompt: str):
        raise _rate_limit_error()

    async def fake_groq_ainvoke(self, prompt: str):
        raise llm.LLMServiceError(
            "Groq is temporarily unavailable. Please retry shortly.",
            status_code=503,
        )

    monkeypatch.setattr(llm.gemini_llm.__class__, "ainvoke", fake_gemini_ainvoke)
    monkeypatch.setattr(ChatGroq, "ainvoke", fake_groq_ainvoke)

    async def run():
        try:
            await llm.call_llm("hello")
        except llm.LLMServiceError as exc:
            assert exc.status_code == 503
            assert exc.retry_after == 55
            assert exc.detail == "Gemini is rate limited and Groq fallback is unavailable. Please retry shortly."
            return
        raise AssertionError("Expected LLMServiceError")

    asyncio.run(run())
