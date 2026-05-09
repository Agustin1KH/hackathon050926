"""Live LLM smoke test. Skipped unless RUN_LIVE_LLM=1 is set."""

from __future__ import annotations

import os

import pytest

from synthaudience.llm import get_llm_client
from synthaudience.models import Persona, Segment
from synthaudience.personas.generator import (
    PERSONA_JSON_SCHEMA,
    _generate_one,
)

requires_live = pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM") != "1",
    reason="Set RUN_LIVE_LLM=1 to run live API tests",
)


@requires_live
@pytest.mark.asyncio
async def test_live_persona_generation_returns_valid_schema():
    seg = Segment(
        id="us_powerlifter",
        weight=1.0,
        demographics={"country": "US", "age_range": [22, 38], "language": "en"},
        psychographics={"values": ["strength", "discipline"], "motivations": ["hit PR"]},
        interests=["r/powerlifting", "r/weightroom"],
        vocabulary_examples=[
            "RPE 8 felt smooth today",
            "Form check on my bench please",
            "Sheiko week 4 is brutal",
        ],
    )
    llm = get_llm_client()
    persona = await _generate_one(seg, llm)
    assert isinstance(persona, Persona)
    # Spot-check a few schema-required fields are non-empty
    assert persona.display_name
    assert persona.bio
    assert persona.tone_examples
    assert PERSONA_JSON_SCHEMA["required"]
