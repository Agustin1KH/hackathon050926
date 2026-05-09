"""Persona generator: distribution math + LLM expansion via FakeLLM."""

from __future__ import annotations


import pytest

from synthaudience.llm import FakeLLMClient
from synthaudience.models import AudienceSpec, Segment
from synthaudience.personas.generator import allocate_segments, generate_personas


def _seg(sid: str, weight: float) -> Segment:
    return Segment(
        id=sid,
        weight=weight,
        demographics={"country": "US", "age_range": [18, 40]},
        psychographics={"values": ["x"], "motivations": ["y"]},
        interests=["r/test"],
        vocabulary_examples=["one", "two", "three", "four", "five"],
    )


def test_allocate_segments_equal_weights():
    spec = AudienceSpec(
        name="t1",
        total_agents=12,
        segments=[
            _seg("a", 0.25),
            _seg("b", 0.25),
            _seg("c", 0.25),
            _seg("d", 0.25),
        ],
    )
    counts = allocate_segments(spec)
    assert counts == {"a": 3, "b": 3, "c": 3, "d": 3}
    assert sum(counts.values()) == 12


def test_allocate_segments_largest_remainder():
    """7 agents, weights 0.5 / 0.3 / 0.2 -> floors 3/2/1 = 6, remainder goes to 'a' (0.5)."""
    spec = AudienceSpec(
        name="t2",
        total_agents=7,
        segments=[
            _seg("a", 0.5),
            _seg("b", 0.3),
            _seg("c", 0.2),
        ],
    )
    counts = allocate_segments(spec)
    assert counts == {"a": 4, "b": 2, "c": 1}
    assert sum(counts.values()) == 7


def _persona_blob(name: str) -> dict:
    return {
        "display_name": name,
        "age": 28,
        "country": "US",
        "occupation": "engineer",
        "bio": "Lifts heavy and posts often. Loves squats. Active in r/powerlifting.",
        "tone_examples": ["Hit a PR today", "RPE 8 felt easy", "Form check please"],
        "interest_graph": ["r/powerlifting", "r/weightroom"],
        "posting_ratio": 0.4,
    }


@pytest.mark.asyncio
async def test_generate_personas_idempotent(temp_db, fitness_spec):
    # Queue 12 valid persona blobs for the first run
    fake = FakeLLMClient(responses=[_persona_blob(f"agent_{i}") for i in range(12)])
    personas = await generate_personas(fitness_spec, llm=fake)

    assert len(personas) == 12
    by_seg: dict[str, int] = {}
    for p in personas:
        by_seg[p.segment_id] = by_seg.get(p.segment_id, 0) + 1
    assert by_seg == {
        "us_powerlifter": 3,
        "us_bodybuilder": 3,
        "eu_powerlifter": 3,
        "eu_bodybuilder": 3,
    }

    # Second run with no queued responses should be a no-op (no LLM calls needed)
    fake2 = FakeLLMClient(responses=[])
    personas2 = await generate_personas(fitness_spec, llm=fake2)
    assert len(personas2) == 12
    assert len(fake2.calls) == 0


@pytest.mark.asyncio
async def test_generate_personas_retry_on_validation_error(temp_db):
    spec = AudienceSpec(name="solo", total_agents=1, segments=[_seg("only", 1.0)])
    bad = {"display_name": "x"}  # missing required fields
    good = _persona_blob("recovered")
    fake = FakeLLMClient(responses=[bad, good])
    personas = await generate_personas(spec, llm=fake)
    assert len(personas) == 1
    assert personas[0].display_name == "recovered"
    assert len(fake.calls) == 2  # one bad, one retry
