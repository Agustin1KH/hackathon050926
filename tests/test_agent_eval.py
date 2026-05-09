"""Agent.evaluate() with the FakeLLM."""

from __future__ import annotations


import pytest

from synthaudience.agents.agent import Agent
from synthaudience.llm import FakeLLMClient
from synthaudience.models import AgentScore, ContentPayload, Persona


def _persona() -> Persona:
    return Persona(
        segment_id="us_powerlifter",
        display_name="Mike",
        age=30,
        country="US",
        occupation="welder",
        bio="Trains in a garage gym, runs Sheiko, posts the occasional form check.",
        tone_examples=["Squats felt heavy today", "RPE 9 on bench, brutal", "Form check please"],
        interest_graph=["r/powerlifting", "r/weightroom"],
        posting_ratio=0.3,
    )


def _content() -> ContentPayload:
    return ContentPayload(
        kind="instagram_post",
        title="5 cues that fixed my squat depth",
        body="Some content body here.",
        media_description="Lifter at the bottom of a squat.",
    )


def _valid_blob(comment: str = "Solid cues, screwing the feet in is underrated") -> dict:
    return {
        "like_score": 8,
        "engage_probability": 0.7,
        "share_probability": 0.4,
        "sentiment": "positive",
        "comment": comment,
        "suggestion": "Add a short clip of the cues being applied",
    }


@pytest.mark.asyncio
async def test_evaluate_happy_path():
    fake = FakeLLMClient(responses=[_valid_blob()])
    agent = Agent(persona=_persona(), llm=fake)
    score = await agent.evaluate(_content())
    assert isinstance(score, AgentScore)
    assert score.like_score == 8
    assert score.sentiment == "positive"
    assert score.agent_id == agent.persona.id
    assert score.raw_json["suggestion"]
    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_evaluate_retry_then_success():
    bad = {"like_score": "eight"}  # wrong type
    fake = FakeLLMClient(responses=[bad, _valid_blob()])
    agent = Agent(persona=_persona(), llm=fake)
    score = await agent.evaluate(_content())
    assert score is not None
    assert score.like_score == 8
    assert len(fake.calls) == 2
    # the retry prompt should mention the validation failure
    assert "failed validation" in fake.calls[1]["user"]


@pytest.mark.asyncio
async def test_evaluate_two_failures_returns_none():
    fake = FakeLLMClient(responses=[{"oops": True}, {"still": "broken"}])
    agent = Agent(persona=_persona(), llm=fake)
    score = await agent.evaluate(_content())
    assert score is None
    assert len(fake.calls) == 2


@pytest.mark.asyncio
async def test_evaluate_clips_overlong_comment():
    long_comment = "x" * 500
    fake = FakeLLMClient(responses=[_valid_blob(comment=long_comment)])
    agent = Agent(persona=_persona(), llm=fake)
    score = await agent.evaluate(_content())
    assert score is not None
    assert len(score.comment) == 280


class _StubMemory:
    def __init__(self, hits: list[str]):
        self.hits = hits
        self.queries: list[tuple[str, str, int]] = []

    def recall(self, agent_id: str, query: str, k: int = 10) -> list[str]:
        self.queries.append((agent_id, query, k))
        return self.hits


@pytest.mark.asyncio
async def test_evaluate_uses_memory_recall():
    memory = _StubMemory(hits=["Last week saw a great squat depth tutorial on r/powerlifting"])
    fake = FakeLLMClient(responses=[_valid_blob()])
    agent = Agent(persona=_persona(), llm=fake, memory=memory)
    score = await agent.evaluate(_content())
    assert score is not None
    assert len(memory.queries) == 1
    # the eval prompt should mention the recalled memory
    assert "squat depth tutorial" in fake.calls[0]["user"]
