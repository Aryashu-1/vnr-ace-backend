import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
from core.llm import LLMServiceError


def test_admissions_endpoint_falls_back_when_llm_is_rate_limited(monkeypatch):
    async def fake_ainvoke(initial_state, config=None):
        raise LLMServiceError(
            "The AI provider is temporarily rate limited. Please retry in about a minute.",
            status_code=429,
            retry_after=60,
        )

    monkeypatch.setattr("routes.v1.agents.admissions_graph.ainvoke", fake_ainvoke)

    client = TestClient(app)
    response = client.post(
        "/api/v1/agents/admissions",
        json={"message": "Tell me about CSE admissions and placements"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["route"] in {"department_query", "faq"}
    assert body["reply"]
    assert body["metadata"]["fallback"] == "local_admissions_data"
