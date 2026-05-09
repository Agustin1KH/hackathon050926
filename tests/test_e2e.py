"""End-to-end: spec -> personas -> evaluation -> aggregated report, all stubbed LLM."""

from __future__ import annotations

import json
import uuid

import pytest

from synthaudience.evaluation.runner import run_evaluation
from synthaudience.llm import FakeLLMClient
from synthaudience.models import AudienceSpec, ContentPayload, Segment
from synthaudience.personas.generator import generate_personas


def _seg(sid: str) -> Segment:
    return Segment(
        id=sid,
        weight=1 / 3,
        demographics={"country": "US", "age_range": [20, 40]},
        psychographics={"values": ["v"], "motivations": ["m"]},
        interests=["r/x"],
        vocabulary_examples=["a", "b", "c", "d", "e"],
    )


def _spec_six_agents() -> AudienceSpec:
    return AudienceSpec(
        name="e2e-test",
        total_agents=6,
        segments=[_seg("alpha"), _seg("beta"), _seg("gamma")],
    )


def _persona_blob(name: str) -> dict:
    return {
        "display_name": name,
        "age": 28,
        "country": "US",
        "occupation": "engineer",
        "bio": "Lifts heavy. Reads forums. Comments occasionally.",
        "tone_examples": ["a", "b", "c"],
        "interest_graph": ["r/x", "r/y"],
        "posting_ratio": 0.3,
    }


def _score_blob(sentiment: str, score: int, comment: str) -> dict:
    return {
        "like_score": score,
        "engage_probability": min(0.1 * score, 1.0),
        "share_probability": min(0.05 * score, 1.0),
        "sentiment": sentiment,
        "comment": comment,
        "suggestion": "More form cues",
    }


def _make_responder():
    """A FakeLLM responder that switches by prompt content."""
    persona_counter = {"n": 0}

    def respond(system: str, user: str, model: str | None, schema: dict | None):
        # Persona generation prompts mention "audience segment"
        if "Create one persona" in user:
            persona_counter["n"] += 1
            return _persona_blob(f"e2e_agent_{persona_counter['n']}")

        # Eval prompts mention "Score the content"
        if "Score the content" in user:
            n = persona_counter["n"]  # alternates: pos / neu / neg by parity-ish
            sentiments = ["positive", "neutral", "negative"]
            sent = sentiments[(n + len(user)) % 3]
            score = {"positive": 8, "neutral": 5, "negative": 2}[sent]
            return _score_blob(sent, score, f"as a {sent} reader, this hits like {score}/10")

        # Theme prompts mention "Extract 3-5 short, distinct themes"
        if "Extract 3-5" in user:
            if "positive" in user:
                return {"themes": ["clear cues", "actionable steps"]}
            if "negative" in user:
                return {"themes": ["lacks evidence", "tired tropes"]}
            return {"themes": ["middle of the road"]}

        raise AssertionError(f"Unexpected prompt: {user[:120]}...")

    return respond


@pytest.mark.asyncio
async def test_end_to_end_six_agents(temp_db):
    fake = FakeLLMClient(responder=_make_responder())

    spec = _spec_six_agents()
    personas = await generate_personas(spec, llm=fake)
    assert len(personas) == 6
    by_seg: dict[str, int] = {}
    for p in personas:
        by_seg[p.segment_id] = by_seg.get(p.segment_id, 0) + 1
    assert by_seg == {"alpha": 2, "beta": 2, "gamma": 2}

    content = ContentPayload(
        kind="instagram_post",
        title="5 cues that fixed my squat depth",
        body="Long body about squatting depth and the cues that fixed it.",
        media_description="Bottom of a squat, chalk, grey gym.",
    )
    run_id = uuid.uuid4()
    report = await run_evaluation(content, run_id, llm=fake)

    # Report shape
    assert report.run_id == run_id
    assert report.content_id == content.id
    assert report.overall["n"] == 6
    assert set(report.by_segment.keys()) == {"alpha", "beta", "gamma"}
    for seg in ("alpha", "beta", "gamma"):
        assert report.by_segment[seg]["n"] == 2

    # Sentiment buckets exist (responder generates a mix), themes pulled through
    assert isinstance(report.top_themes_positive, list)
    assert isinstance(report.top_themes_negative, list)
    assert len(report.representative_comments) == 3

    # Scores persisted
    from synthaudience.db import RunRow, ScoreRow, get_session_factory

    factory = get_session_factory()
    with factory() as session:
        score_rows = session.query(ScoreRow).filter_by(run_id=str(run_id)).all()
        assert len(score_rows) == 6
        run_row = session.query(RunRow).filter_by(id=str(run_id)).first()
        assert run_row is not None
        assert run_row.report_json
        # Round-trip the persisted report
        persisted = json.loads(run_row.report_json)
        assert persisted["overall"]["n"] == 6
