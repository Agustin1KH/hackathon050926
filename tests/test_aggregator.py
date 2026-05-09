"""Aggregator math: per-segment means, sentiment distribution, theme extraction."""

from __future__ import annotations

import uuid

import pytest

from synthaudience.evaluation.aggregator import build_report
from synthaudience.llm import FakeLLMClient
from synthaudience.models import AgentScore, Persona


def _persona(seg: str) -> Persona:
    return Persona(
        segment_id=seg,
        display_name=f"agent_{seg}",
        age=30,
        country="US",
        occupation="x",
        bio="x. y. z.",
        tone_examples=["a", "b", "c"],
        interest_graph=["r/x"],
        posting_ratio=0.5,
    )


def _score(agent_id: uuid.UUID, content_id: uuid.UUID, **kwargs) -> AgentScore:
    base = {
        "like_score": 5,
        "engage_probability": 0.5,
        "share_probability": 0.2,
        "sentiment": "neutral",
        "comment": "ok",
        "suggestion": "x",
        "raw_json": {},
    }
    base.update(kwargs)
    return AgentScore(agent_id=agent_id, content_id=content_id, **base)


@pytest.mark.asyncio
async def test_build_report_means_and_dist():
    content_id = uuid.uuid4()
    run_id = uuid.uuid4()

    # 3 segments x 2 agents
    personas = []
    for seg in ("a", "b", "c"):
        for _ in range(2):
            personas.append(_persona(seg))

    # Hand-pick scores so we can verify the math
    scores = []
    p_iter = iter(personas)

    # segment a: 8/0.8/0.6 positive  ;  6/0.4/0.2 positive  -> means 7/0.6/0.4, dist 100% positive
    a1, a2 = next(p_iter), next(p_iter)
    scores.append(
        _score(
            a1.id,
            content_id,
            like_score=8,
            engage_probability=0.8,
            share_probability=0.6,
            sentiment="positive",
            comment="loved cue 1",
        )
    )
    scores.append(
        _score(
            a2.id,
            content_id,
            like_score=6,
            engage_probability=0.4,
            share_probability=0.2,
            sentiment="positive",
            comment="great breakdown",
        )
    )

    # segment b: 4/0.5/0.1 neutral  ;  4/0.3/0.0 neutral
    b1, b2 = next(p_iter), next(p_iter)
    scores.append(
        _score(
            b1.id,
            content_id,
            like_score=4,
            engage_probability=0.5,
            share_probability=0.1,
            sentiment="neutral",
            comment="meh",
        )
    )
    scores.append(
        _score(
            b2.id,
            content_id,
            like_score=4,
            engage_probability=0.3,
            share_probability=0.0,
            sentiment="neutral",
            comment="seen this before",
        )
    )

    # segment c: 2/0.1/0.0 negative ; 0/0.0/0.0 negative
    c1, c2 = next(p_iter), next(p_iter)
    scores.append(
        _score(
            c1.id,
            content_id,
            like_score=2,
            engage_probability=0.1,
            share_probability=0.0,
            sentiment="negative",
            comment="form is wrong",
        )
    )
    scores.append(
        _score(
            c2.id,
            content_id,
            like_score=0,
            engage_probability=0.0,
            share_probability=0.0,
            sentiment="negative",
            comment="bad cues",
        )
    )

    fake = FakeLLMClient(
        responses=[
            {"themes": ["clear cues", "actionable tips"]},  # positive
            {"themes": ["form concerns", "lacks depth proof"]},  # negative
        ]
    )

    report = await build_report(run_id, content_id, scores, personas, fake)

    # overall: like = (8+6+4+4+2+0)/6 = 4
    assert report.overall["like_score"] == pytest.approx(4.0)
    # engage: (0.8+0.4+0.5+0.3+0.1+0.0)/6 = 2.1/6 = 0.35
    assert report.overall["engage_probability"] == pytest.approx(0.35, abs=1e-3)
    # share: (0.6+0.2+0.1+0+0+0)/6 = 0.9/6 = 0.15
    assert report.overall["share_probability"] == pytest.approx(0.15, abs=1e-3)
    # sentiment dist: 2 pos / 2 neu / 2 neg
    assert report.overall["sentiment_dist"] == {
        "positive": pytest.approx(0.3333, abs=1e-3),
        "neutral": pytest.approx(0.3333, abs=1e-3),
        "negative": pytest.approx(0.3333, abs=1e-3),
    }

    # per segment
    assert report.by_segment["a"]["like_score"] == pytest.approx(7.0)
    assert report.by_segment["b"]["like_score"] == pytest.approx(4.0)
    assert report.by_segment["c"]["like_score"] == pytest.approx(1.0)
    assert report.by_segment["a"]["sentiment_dist"]["positive"] == pytest.approx(1.0)
    assert report.by_segment["c"]["sentiment_dist"]["negative"] == pytest.approx(1.0)

    # themes flowed through
    assert report.top_themes_positive == ["clear cues", "actionable tips"]
    assert report.top_themes_negative == ["form concerns", "lacks depth proof"]

    # representative comments: one per segment
    seg_ids = {c["segment_id"] for c in report.representative_comments}
    assert seg_ids == {"a", "b", "c"}


@pytest.mark.asyncio
async def test_build_report_skips_empty_buckets():
    content_id = uuid.uuid4()
    run_id = uuid.uuid4()
    personas = [_persona("a"), _persona("a")]
    scores = [
        _score(personas[0].id, content_id, sentiment="positive", comment="great"),
        _score(personas[1].id, content_id, sentiment="positive", comment="loved it"),
    ]

    # Only ONE response queued because only the positive bucket should trigger an LLM call
    fake = FakeLLMClient(responses=[{"themes": ["enthusiasm"]}])

    report = await build_report(run_id, content_id, scores, personas, fake)
    assert report.top_themes_positive == ["enthusiasm"]
    assert report.top_themes_negative == []
    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_build_report_handles_zero_scores():
    content_id = uuid.uuid4()
    run_id = uuid.uuid4()
    fake = FakeLLMClient(responses=[])
    report = await build_report(run_id, content_id, [], [], fake)
    assert report.overall["n"] == 0
    assert report.by_segment == {}
    assert report.top_themes_positive == []
    assert report.top_themes_negative == []
    assert report.representative_comments == []
