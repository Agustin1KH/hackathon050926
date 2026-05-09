"""API smoke tests using FastAPI's TestClient.

We monkeypatch the LLM client at the import site so the API hits our FakeLLMClient
instead of Anthropic. The DB is per-test via the `temp_db` fixture.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from synthaudience.llm import FakeLLMClient


def _spec_blob() -> dict:
    return {
        "name": "Test Audience!",
        "total_agents": 4,
        "segments": [
            {
                "id": "seg_a",
                "weight": 0.5,
                "demographics": {
                    "country": "US",
                    "age_range": [20, 40],
                    "gender_dist": {"male": 0.5, "female": 0.5},
                    "language": "en",
                },
                "psychographics": {"values": ["v"], "motivations": ["m"]},
                "interests": ["r/x"],
                "vocabulary_examples": ["a", "b", "c", "d", "e"],
            },
            {
                "id": "seg_b",
                "weight": 0.5,
                "demographics": {
                    "country": "EU",
                    "age_range": [20, 40],
                    "gender_dist": {"male": 0.5, "female": 0.5},
                    "language": "en",
                },
                "psychographics": {"values": ["v"], "motivations": ["m"]},
                "interests": ["r/y"],
                "vocabulary_examples": ["a", "b", "c", "d", "e"],
            },
        ],
    }


def _persona_blob(name: str) -> dict:
    return {
        "display_name": name,
        "age": 30,
        "country": "US",
        "occupation": "x",
        "bio": "Lifts heavy. Posts often. Knows form.",
        "tone_examples": ["a", "b", "c"],
        "interest_graph": ["r/x", "r/y"],
        "posting_ratio": 0.4,
    }


@pytest.fixture
def client(temp_db, monkeypatch):
    fake = FakeLLMClient(responses=[_spec_blob()] + [_persona_blob(f"a{i}") for i in range(4)])

    # Patch get_llm_client at the api import site (where it's used inside the endpoint).
    import synthaudience.api as api_mod

    monkeypatch.setattr(api_mod, "get_llm_client", lambda: fake)

    # Also patch where generator.generate_personas reaches for it
    import synthaudience.personas.generator as gen_mod

    monkeypatch.setattr(gen_mod, "get_llm_client", lambda: fake)

    return TestClient(api_mod.app), fake


def test_index_html_served(client):
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert "<html" in resp.text.lower()
    assert "synthaudience" in resp.text.lower()


def test_audience_from_text_and_generate(client):
    c, fake = client

    # 1. Free-text -> AudienceSpec
    r = c.post(
        "/audience/from-text",
        json={"description": "Half tennis players, half soccer fans", "total_agents": 4},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "audience_id" in data
    assert data["spec"]["total_agents"] == 4
    assert data["spec"]["name"] == "test-audience"  # slugified
    assert len(data["spec"]["segments"]) == 2

    # 2. Generate personas for that audience
    r2 = c.post("/personas/generate", json={"audience_id": data["audience_id"]})
    assert r2.status_code == 200, r2.text
    gen = r2.json()
    assert gen["count"] == 4
    assert len(gen["personas"]) == 4
    by_seg: dict[str, int] = {}
    for p in gen["personas"]:
        by_seg[p["segment_id"]] = by_seg.get(p["segment_id"], 0) + 1
    assert by_seg == {"seg_a": 2, "seg_b": 2}

    # 3. GET /personas should return the same set
    r3 = c.get("/personas")
    assert r3.status_code == 200
    assert len(r3.json()) == 4


def test_audience_from_text_rejects_empty(client):
    c, _ = client
    r = c.post("/audience/from-text", json={"description": "   "})
    assert r.status_code == 400


def test_audience_from_text_502_on_repeated_failure(client, monkeypatch):
    c, _ = client

    bad_fake = FakeLLMClient(responses=[{"oops": True}, {"still": "broken"}])

    import synthaudience.api as api_mod

    monkeypatch.setattr(api_mod, "get_llm_client", lambda: bad_fake)

    r = c.post("/audience/from-text", json={"description": "valid input"})
    assert r.status_code == 502
