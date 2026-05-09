"""Discovery cron: each persona browses one of its subreddits per cycle."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from synthaudience.agents.agent import Agent
from synthaudience.config import get_settings
from synthaudience.db import MemoryEventRow, get_session_factory
from synthaudience.discovery.reddit import fetch_top_posts
from synthaudience.llm import LLMClient, get_llm_client
from synthaudience.models import Persona

logger = logging.getLogger(__name__)


def _last_visited(agent_id: str) -> dict[str, datetime]:
    """Most recent browse timestamp per subreddit for an agent."""
    factory = get_session_factory()
    with factory() as session:
        rows = session.query(MemoryEventRow).filter_by(agent_id=agent_id, kind="browse").all()
        out: dict[str, datetime] = {}
        for r in rows:
            try:
                meta = json.loads(r.metadata_json)
            except json.JSONDecodeError:
                continue
            sub = meta.get("subreddit")
            if not sub:
                continue
            if r.created_at and (sub not in out or r.created_at > out[sub]):
                out[sub] = r.created_at
        return out


def _pick_subreddit(persona: Persona) -> str | None:
    if not persona.interest_graph:
        return None
    visits = _last_visited(str(persona.id))

    def _ts(sub: str) -> float:
        # SQLite stores naive datetimes; compare as POSIX timestamps to avoid
        # mixing tz-aware and tz-naive values from different sources.
        dt = visits.get(sub)
        if dt is None:
            return 0.0
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()

    sorted_subs = sorted(persona.interest_graph, key=_ts)
    return sorted_subs[0]


def _load_personas() -> list[Persona]:
    from synthaudience.db import PersonaRow

    factory = get_session_factory()
    with factory() as session:
        rows = session.query(PersonaRow).all()
        return [
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
            for r in rows
        ]


async def run_browse_once(
    llm: LLMClient | None = None,
    fetcher=fetch_top_posts,
    memory_factory=None,
) -> dict:
    """One pass: each persona browses one of its subreddits, writes reflections to memory.

    `fetcher(subreddit, since_ts, limit)` is injectable for tests.
    `memory_factory(persona)` returns a MemoryStore or None.
    """
    llm = llm or get_llm_client()
    personas = _load_personas()
    if not personas:
        return {"agents_browsed": 0, "memories_added": 0}

    since_ts = (datetime.now(timezone.utc) - timedelta(days=1)).timestamp()
    sem = asyncio.Semaphore(8)

    async def browse_one(p: Persona) -> int:
        async with sem:
            sub = _pick_subreddit(p)
            if sub is None:
                return 0
            posts = fetcher(sub, since_ts=since_ts, limit=5)
            if not posts:
                logger.info("No posts found for %s for agent %s", sub, p.id)
                return 0
            mem = memory_factory(p) if memory_factory else None
            agent = Agent(persona=p, llm=llm, memory=mem)
            return await agent.browse(sub, posts)

    counts = await asyncio.gather(*(browse_one(p) for p in personas))
    return {
        "agents_browsed": sum(1 for c in counts if c > 0),
        "memories_added": int(sum(counts)),
    }


def start_scheduler(llm: LLMClient | None = None):
    """Register the browse job on an in-process APScheduler. Returns the scheduler."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    settings = get_settings()
    sched = BackgroundScheduler()

    def _tick() -> None:
        try:
            asyncio.run(run_browse_once(llm=llm))
        except Exception as e:
            logger.exception("Browse tick failed: %s", e)

    sched.add_job(
        _tick,
        trigger=IntervalTrigger(minutes=settings.discovery_interval_minutes),
        id="browse",
        replace_existing=True,
    )
    sched.start()
    return sched
