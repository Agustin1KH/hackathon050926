"""Persona generation: stratified allocation + LLM expansion, persisted to SQLite."""

from __future__ import annotations

import asyncio
import json
import logging
import math
from typing import Iterable

from pydantic import ValidationError

from synthaudience.db import PersonaRow, get_session_factory
from synthaudience.llm import LLMClient, get_llm_client
from synthaudience.models import AudienceSpec, Persona, Segment
from synthaudience.personas.prompts import PERSONA_SYSTEM, render_persona_prompt

logger = logging.getLogger(__name__)


PERSONA_JSON_SCHEMA = {
    "type": "object",
    "required": [
        "display_name",
        "age",
        "country",
        "occupation",
        "bio",
        "tone_examples",
        "interest_graph",
        "posting_ratio",
    ],
    "properties": {
        "display_name": {"type": "string"},
        "age": {"type": "integer"},
        "country": {"type": "string"},
        "occupation": {"type": "string"},
        "bio": {"type": "string"},
        "tone_examples": {"type": "array", "items": {"type": "string"}},
        "interest_graph": {"type": "array", "items": {"type": "string"}},
        "posting_ratio": {"type": "number"},
    },
}


def allocate_segments(spec: AudienceSpec) -> dict[str, int]:
    """Largest-remainder rounding: distribute total_agents across segments by weight."""
    total = spec.total_agents
    raw = [(seg.id, seg.weight * total) for seg in spec.segments]
    floors = {sid: math.floor(v) for sid, v in raw}
    assigned = sum(floors.values())
    remaining = total - assigned

    # rank by largest fractional remainder, tie-break by original order
    remainders = sorted(
        enumerate(raw),
        key=lambda item: (-(item[1][1] - math.floor(item[1][1])), item[0]),
    )
    for i in range(remaining):
        sid = remainders[i][1][0]
        floors[sid] += 1
    return floors


async def _generate_one(
    segment: Segment,
    llm: LLMClient,
) -> Persona | None:
    user = render_persona_prompt(segment)

    for attempt in range(2):
        try:
            data = await llm.complete(
                system=PERSONA_SYSTEM,
                user=user,
                json_schema=PERSONA_JSON_SCHEMA,
            )
            if isinstance(data, str):
                data = json.loads(data)
            return Persona(segment_id=segment.id, **data)
        except (ValidationError, json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "Persona validation failed for %s (attempt %d): %s", segment.id, attempt + 1, e
            )
            user = (
                f"{render_persona_prompt(segment)}\n\n"
                f"Your previous response failed validation: {e}. "
                f"Return a corrected JSON object."
            )
    logger.error("Persona generation gave up for %s after 2 attempts", segment.id)
    return None


def _existing_counts(audience_name: str) -> dict[str, int]:
    factory = get_session_factory()
    with factory() as session:
        rows = session.query(PersonaRow).filter_by(audience_name=audience_name).all()
        counts: dict[str, int] = {}
        for r in rows:
            counts[r.segment_id] = counts.get(r.segment_id, 0) + 1
        return counts


def _persist(audience_name: str, personas: Iterable[Persona]) -> None:
    factory = get_session_factory()
    with factory() as session:
        for p in personas:
            session.add(
                PersonaRow(
                    id=str(p.id),
                    audience_name=audience_name,
                    segment_id=p.segment_id,
                    display_name=p.display_name,
                    age=p.age,
                    country=p.country,
                    occupation=p.occupation,
                    bio=p.bio,
                    tone_examples=json.dumps(p.tone_examples),
                    interest_graph=json.dumps(p.interest_graph),
                    posting_ratio=p.posting_ratio,
                    created_at=p.created_at,
                )
            )
        session.commit()


def load_personas(audience_name: str) -> list[Persona]:
    """Read all personas for an audience back as Pydantic models."""
    factory = get_session_factory()
    with factory() as session:
        rows = session.query(PersonaRow).filter_by(audience_name=audience_name).all()
        out: list[Persona] = []
        for r in rows:
            out.append(
                Persona(
                    id=r.id,
                    segment_id=r.segment_id,
                    display_name=r.display_name,
                    age=r.age,
                    country=r.country,
                    occupation=r.occupation,
                    bio=r.bio,
                    tone_examples=json.loads(r.tone_examples),
                    interest_graph=json.loads(r.interest_graph),
                    posting_ratio=r.posting_ratio,
                    created_at=r.created_at,
                )
            )
        return out


async def generate_personas(spec: AudienceSpec, llm: LLMClient | None = None) -> list[Persona]:
    """Generate (or top up) personas for an audience spec. Idempotent by audience name."""
    llm = llm or get_llm_client()
    target = allocate_segments(spec)
    existing = _existing_counts(spec.name)

    # Build the work list: per-segment shortfall.
    by_id = {seg.id: seg for seg in spec.segments}
    work: list[Segment] = []
    for sid, n in target.items():
        gap = n - existing.get(sid, 0)
        for _ in range(max(gap, 0)):
            work.append(by_id[sid])

    sem = asyncio.Semaphore(8)

    async def bounded(seg: Segment) -> Persona | None:
        async with sem:
            return await _generate_one(seg, llm)

    results = await asyncio.gather(*(bounded(seg) for seg in work))
    new_personas = [p for p in results if p is not None]
    _persist(spec.name, new_personas)

    return load_personas(spec.name)
