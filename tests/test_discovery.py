"""Discovery loop with a mocked Reddit fetcher and FakeLLM."""

from __future__ import annotations

import time

import pytest

from synthaudience.discovery.reddit import RedditPost
from synthaudience.discovery.scheduler import run_browse_once
from synthaudience.llm import FakeLLMClient
from synthaudience.models import AudienceSpec, Segment
from synthaudience.personas.generator import generate_personas


def _seg(sid: str) -> Segment:
    return Segment(
        id=sid,
        weight=0.5,
        demographics={"country": "US", "age_range": [20, 40]},
        psychographics={"values": ["v"], "motivations": ["m"]},
        interests=["r/x", "r/y"],
        vocabulary_examples=["a", "b", "c", "d", "e"],
    )


def _persona_blob(name: str, interests: list[str]) -> dict:
    return {
        "display_name": name,
        "age": 30,
        "country": "US",
        "occupation": "x",
        "bio": "x. y. z.",
        "tone_examples": ["a", "b", "c"],
        "interest_graph": interests,
        "posting_ratio": 0.5,
    }


def _fake_posts(subreddit: str, since_ts=None, limit: int = 5) -> list[RedditPost]:
    base = time.time() - 3600
    return [
        RedditPost(
            id=f"{subreddit}_p{i}",
            title=f"Post {i} on {subreddit}",
            selftext=f"Body of post {i}",
            score=10,
            created_utc=base - i,
            permalink=f"/r/{subreddit}/comments/p{i}",
            subreddit=subreddit,
        )
        for i in range(3)
    ]


def _browse_reflections() -> str:
    return (
        "1. Solid post, exactly the kind of cue I'd save.\n"
        "2. Pretty generic but not bad.\n"
        "3. Hard disagree, the form is sketchy."
    )


@pytest.mark.asyncio
async def test_run_browse_once_writes_memories(temp_db):
    spec = AudienceSpec(
        name="discovery-test",
        total_agents=2,
        segments=[_seg("alpha")],
    )
    persona_responses = [_persona_blob(f"a_{i}", ["r/x", "r/y"]) for i in range(2)]
    fake = FakeLLMClient(responses=persona_responses)
    personas = await generate_personas(spec, llm=fake)
    assert len(personas) == 2

    # Now seed a separate FakeLLM that returns reflections for each browse call.
    browse_llm = FakeLLMClient(responses=[_browse_reflections() for _ in range(2)])

    result = await run_browse_once(llm=browse_llm, fetcher=_fake_posts)
    assert result["agents_browsed"] == 2
    # 2 agents * 3 posts each = 6 reflections written
    assert result["memories_added"] == 6

    # Verify the SQLite audit log got entries
    from synthaudience.db import MemoryEventRow, get_session_factory

    with get_session_factory()() as session:
        rows = session.query(MemoryEventRow).filter_by(kind="browse").all()
        assert len(rows) == 6
        # each row's metadata records subreddit + post_id
        for r in rows:
            import json

            meta = json.loads(r.metadata_json)
            assert meta["subreddit"] in {"r/x", "r/y"}
            assert meta["post_id"].startswith("r/")


@pytest.mark.asyncio
async def test_run_browse_once_least_recently_visited(temp_db):
    """After visiting r/x, the next browse should pick r/y."""
    spec = AudienceSpec(
        name="lrv-test",
        total_agents=1,
        segments=[_seg("alpha")],
    )
    fake = FakeLLMClient(responses=[_persona_blob("a", ["r/x", "r/y"])])
    await generate_personas(spec, llm=fake)

    browse_llm = FakeLLMClient(responses=[_browse_reflections(), _browse_reflections()])
    await run_browse_once(llm=browse_llm, fetcher=_fake_posts)
    await run_browse_once(llm=browse_llm, fetcher=_fake_posts)

    from synthaudience.db import MemoryEventRow, get_session_factory
    import json

    with get_session_factory()() as session:
        rows = (
            session.query(MemoryEventRow).filter_by(kind="browse").order_by(MemoryEventRow.id).all()
        )
        subs_visited = []
        last_sub = None
        for r in rows:
            sub = json.loads(r.metadata_json)["subreddit"]
            if sub != last_sub:
                subs_visited.append(sub)
                last_sub = sub
        # Two browse cycles -> two distinct subs visited (least-recently-visited swap)
        assert subs_visited == ["r/x", "r/y"] or subs_visited == ["r/y", "r/x"]
        assert len(set(subs_visited)) == 2
