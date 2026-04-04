import asyncio
import sys
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from openai import RateLimitError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
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
    async def fake_ainvoke(self, prompt: str):
        raise _rate_limit_error()

    monkeypatch.setattr(llm.groq_llm.__class__, "ainvoke", fake_ainvoke)

    async def run():
        try:
            await llm.call_llm("hello")
        except llm.LLMServiceError as exc:
            assert exc.status_code == 429
            assert exc.retry_after == 55
            assert "rate limited" in exc.detail.lower()
            return
        raise AssertionError("Expected LLMServiceError")

    asyncio.run(run())


def test_global_handler_returns_429(monkeypatch):
    async def fake_ainvoke(self, prompt: str):
        raise _rate_limit_error()

    monkeypatch.setattr(llm.groq_llm.__class__, "ainvoke", fake_ainvoke)

    client = TestClient(app)
    response = client.post(
        "/api/v1/agents/admissions",
        json={"message": "What are the CSE eligibility criteria?"},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "55"
    assert response.json()["detail"] == "The AI provider is temporarily rate limited. Please retry in about a minute."
