"""Fan content out to all personas in parallel; persist scores; build report."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from synthaudience.agents.agent import Agent
from synthaudience.db import RunRow, ScoreRow, get_session_factory
from synthaudience.evaluation.aggregator import build_report
from synthaudience.llm import LLMClient, get_llm_client
from synthaudience.models import AgentScore, ContentPayload, EvaluationReport, Persona

logger = logging.getLogger(__name__)


def _load_all_personas(audience_name: str | None) -> list[Persona]:
    """Load personas for a single audience or all audiences if name is None."""
    from synthaudience.db import PersonaRow

    factory = get_session_factory()
    with factory() as session:
        q = session.query(PersonaRow)
        if audience_name is not None:
            q = q.filter_by(audience_name=audience_name)
        rows = q.all()
        out = []
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


def _persist_run(run_id: uuid.UUID, content: ContentPayload) -> None:
    factory = get_session_factory()
    with factory() as session:
        session.add(
            RunRow(
                id=str(run_id),
                content_id=str(content.id),
                content_json=content.model_dump_json(),
            )
        )
        session.commit()


def _persist_scores(run_id: uuid.UUID, scores: list[AgentScore]) -> None:
    if not scores:
        return
    factory = get_session_factory()
    with factory() as session:
        for s in scores:
            session.add(
                ScoreRow(
                    run_id=str(run_id),
                    agent_id=str(s.agent_id),
                    content_id=str(s.content_id),
                    like_score=s.like_score,
                    engage_probability=s.engage_probability,
                    share_probability=s.share_probability,
                    sentiment=s.sentiment,
                    comment=s.comment,
                    suggestion=s.suggestion,
                    raw_json=json.dumps(s.raw_json),
                )
            )
        session.commit()


def _persist_report(run_id: uuid.UUID, report: EvaluationReport) -> None:
    factory = get_session_factory()
    with factory() as session:
        row = session.query(RunRow).filter_by(id=str(run_id)).first()
        if row is None:
            return
        row.report_json = report.model_dump_json()
        session.commit()


async def run_evaluation(
    content: ContentPayload,
    run_id: uuid.UUID,
    llm: LLMClient | None = None,
    audience_name: str | None = None,
    memory_factory=None,
) -> EvaluationReport:
    """Score `content` with every persona and return the aggregated report.

    `memory_factory(persona) -> MemoryStore | None` lets callers wire memory recall;
    if None, agents run without memory (still fully functional, just no recall context).
    """
    llm = llm or get_llm_client()
    personas = _load_all_personas(audience_name)
    if not personas:
        raise RuntimeError("No personas found - run generate-personas first.")

    _persist_run(run_id, content)

    sem = asyncio.Semaphore(8)

    async def bounded_eval(p: Persona) -> AgentScore | None:
        async with sem:
            mem = memory_factory(p) if memory_factory else None
            agent = Agent(persona=p, llm=llm, memory=mem)
            return await agent.evaluate(content)

    results = await asyncio.gather(*(bounded_eval(p) for p in personas))
    scores = [r for r in results if r is not None]
    if not scores:
        logger.warning("Run %s produced zero valid scores", run_id)

    _persist_scores(run_id, scores)
    report = await build_report(run_id, content.id, scores, personas, llm)
    _persist_report(run_id, report)
    return report
