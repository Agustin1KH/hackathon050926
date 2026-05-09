"""Free-text -> AudienceSpec parsing."""

from __future__ import annotations

import pytest

from synthaudience.llm import FakeLLMClient
from synthaudience.personas.text_to_spec import (
    _normalize_weights,
    _slug,
    text_to_audience_spec,
)


def _good_spec() -> dict:
    return {
        "name": "Tennis & Soccer Audience!",
        "total_agents": 12,
        "segments": [
            {
                "id": "us_tennis",
                "weight": 0.5,
                "demographics": {
                    "country": "US",
                    "age_range": [18, 50],
                    "gender_dist": {"male": 0.55, "female": 0.45},
                    "language": "en",
                },
                "psychographics": {
                    "values": ["competition", "consistency", "footwork"],
                    "motivations": ["improve serve", "join a club"],
                },
                "interests": ["r/tennis", "r/10s"],
                "vocabulary_examples": [
                    "My slice backhand is finally feeling consistent",
                    "Anyone using poly strings? worth the buzz?",
                    "USTA 4.0 league starts next month, hyped",
                    "Watching Sinner-Alcaraz live, this rally is unreal",
                    "Ankle held up after surgery, slow comeback",
                ],
            },
            {
                "id": "eu_soccer",
                "weight": 0.5,
                "demographics": {
                    "country": "EU",
                    "age_range": [18, 45],
                    "gender_dist": {"male": 0.6, "female": 0.4},
                    "language": "en",
                },
                "psychographics": {
                    "values": ["teamwork", "skill", "tradition"],
                    "motivations": ["follow the league", "join Sunday league"],
                },
                "interests": ["r/soccer", "r/football"],
                "vocabulary_examples": [
                    "Pulisic finishing has been class lately",
                    "Sunday league pitch was a swamp today, brutal",
                    "Anyone running a 4-3-3 in their kickabout?",
                    "Boots collection is getting out of hand, send help",
                    "City-Madrid was peak Champions League football",
                ],
            },
        ],
    }


@pytest.mark.asyncio
async def test_text_to_spec_happy_path():
    fake = FakeLLMClient(responses=[_good_spec()])
    spec = await text_to_audience_spec(
        "100 people, half American tennis players, half European soccer players",
        llm=fake,
        total_agents=12,
    )
    assert spec is not None
    assert spec.total_agents == 12
    assert len(spec.segments) == 2
    assert spec.name == "tennis-soccer-audience"  # slugified
    assert sum(s.weight for s in spec.segments) == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_text_to_spec_normalizes_drifted_weights():
    bad_weights = _good_spec()
    bad_weights["segments"][0]["weight"] = 0.6
    bad_weights["segments"][1]["weight"] = 0.6  # sums to 1.2
    fake = FakeLLMClient(responses=[bad_weights])
    spec = await text_to_audience_spec("desc", llm=fake)
    assert spec is not None
    assert sum(s.weight for s in spec.segments) == pytest.approx(1.0)
    assert spec.segments[0].weight == pytest.approx(0.5)
    assert spec.segments[1].weight == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_text_to_spec_overrides_total_agents():
    """Caller's total_agents wins even if LLM returned a different number."""
    blob = _good_spec()
    blob["total_agents"] = 47  # LLM picked something other than what user asked
    fake = FakeLLMClient(responses=[blob])
    spec = await text_to_audience_spec("desc", llm=fake, total_agents=12)
    assert spec is not None
    assert spec.total_agents == 12


@pytest.mark.asyncio
async def test_text_to_spec_retries_on_bad_json():
    bad = {"missing": "fields"}
    good = _good_spec()
    fake = FakeLLMClient(responses=[bad, good])
    spec = await text_to_audience_spec("desc", llm=fake)
    assert spec is not None
    assert len(fake.calls) == 2


@pytest.mark.asyncio
async def test_text_to_spec_returns_none_on_repeated_failure():
    fake = FakeLLMClient(responses=[{"a": 1}, {"b": 2}])
    spec = await text_to_audience_spec("desc", llm=fake)
    assert spec is None


@pytest.mark.asyncio
async def test_text_to_spec_empty_description_returns_none():
    fake = FakeLLMClient(responses=[])
    spec = await text_to_audience_spec("   ", llm=fake)
    assert spec is None
    assert len(fake.calls) == 0


def test_slug_helper():
    assert _slug("Tennis & Soccer!") == "tennis-soccer"
    assert _slug("UPPERCASE") == "uppercase"
    assert _slug("") == "audience"


def test_normalize_weights_zero_total():
    spec = {"segments": [{"weight": 0}, {"weight": 0}, {"weight": 0}]}
    out = _normalize_weights(spec)
    weights = [s["weight"] for s in out["segments"]]
    assert weights == [pytest.approx(1 / 3)] * 3
