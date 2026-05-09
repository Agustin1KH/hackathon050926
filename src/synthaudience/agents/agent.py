"""Persona-bound agent: holds a persona, an LLM, and (optionally) a memory store."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import ValidationError

from synthaudience.agents.prompts import (
    render_agent_system,
    render_browse_user,
    render_eval_user,
)
from synthaudience.config import get_settings
from synthaudience.llm import LLMClient
from synthaudience.models import AgentScore, ContentPayload, Persona

if TYPE_CHECKING:
    from synthaudience.memory import MemoryStore
    from synthaudience.discovery.reddit import RedditPost

logger = logging.getLogger(__name__)


AGENT_SCORE_SCHEMA = {
    "type": "object",
    "required": [
        "like_score",
        "engage_probability",
        "share_probability",
        "sentiment",
        "comment",
        "suggestion",
    ],
    "properties": {
        "like_score": {"type": "integer", "minimum": 0, "maximum": 10},
        "engage_probability": {"type": "number", "minimum": 0, "maximum": 1},
        "share_probability": {"type": "number", "minimum": 0, "maximum": 1},
        "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
        "comment": {"type": "string", "maxLength": 280},
        "suggestion": {"type": "string"},
    },
}


class Agent:
    def __init__(
        self,
        persona: Persona,
        llm: LLMClient,
        memory: "MemoryStore | None" = None,
        eval_model: str | None = None,
        browse_model: str | None = None,
    ):
        self.persona = persona
        self.llm = llm
        self.memory = memory
        settings = get_settings()
        self.eval_model = eval_model or settings.eval_model
        self.browse_model = browse_model or settings.browse_model

    async def evaluate(self, content: ContentPayload) -> AgentScore | None:
        """Score one piece of content. Retries once on validation failure, returns None on second."""
        recalled: list[str] = []
        if self.memory is not None:
            try:
                query = f"{content.title}\n{content.body}"
                recalled = self.memory.recall(str(self.persona.id), query, k=10)
            except Exception as e:  # memory should never block evaluation
                logger.warning("Memory recall failed for agent %s: %s", self.persona.id, e)

        system = render_agent_system(self.persona)
        user = render_eval_user(content, recalled)

        for attempt in range(2):
            try:
                data = await self.llm.complete(
                    system=system,
                    user=user,
                    model=self.eval_model,
                    json_schema=AGENT_SCORE_SCHEMA,
                )
                if isinstance(data, str):
                    data = json.loads(data)
                # comment may overflow the 280-char limit — clip rather than fail
                if isinstance(data.get("comment"), str) and len(data["comment"]) > 280:
                    data["comment"] = data["comment"][:280]
                return AgentScore(
                    agent_id=self.persona.id,
                    content_id=content.id,
                    like_score=data["like_score"],
                    engage_probability=data["engage_probability"],
                    share_probability=data["share_probability"],
                    sentiment=data["sentiment"],
                    comment=data["comment"],
                    suggestion=data["suggestion"],
                    raw_json=data,
                )
            except (ValidationError, KeyError, ValueError, json.JSONDecodeError) as e:
                logger.warning(
                    "Eval validation failed for agent %s (attempt %d): %s",
                    self.persona.id,
                    attempt + 1,
                    e,
                )
                user = (
                    f"{render_eval_user(content, recalled)}\n\n"
                    f"Your previous response failed validation: {e}. "
                    f"Return a corrected JSON object."
                )
        logger.error("Agent %s gave up evaluating content %s", self.persona.id, content.id)
        return None

    async def browse(self, subreddit: str, posts: "list[RedditPost]") -> int:
        """Read posts in character, write reflections to memory. Returns memory count added."""
        if not posts:
            return 0

        system = render_agent_system(self.persona)
        user = render_browse_user(subreddit, posts)
        try:
            text = await self.llm.complete(system=system, user=user, model=self.browse_model)
        except Exception as e:
            logger.warning("Browse LLM call failed for agent %s: %s", self.persona.id, e)
            return 0

        # The model returns one numbered reflection per post. We'll match by leading number.
        if isinstance(text, dict):
            text = json.dumps(text)
        reflections = _parse_numbered_reflections(text, expected=len(posts))

        added = 0
        ts = datetime.now(timezone.utc).isoformat()
        for post, reflection in zip(posts, reflections):
            if not reflection:
                continue
            entry = f"On {subreddit}, post titled '{post.title}': {reflection}"
            metadata = {
                "kind": "browse",
                "subreddit": subreddit,
                "post_id": post.id,
                "ts": ts,
            }
            if self.memory is not None:
                try:
                    self.memory.add_memory(str(self.persona.id), entry, metadata)
                except Exception as e:
                    logger.warning("Memory write failed for agent %s: %s", self.persona.id, e)
                    continue
            _log_memory_event(str(self.persona.id), "browse", entry, metadata)
            added += 1
        return added


def _parse_numbered_reflections(text: str, expected: int) -> list[str]:
    """Parse '1. text\n2. text\n...' or fall back to one chunk per line."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    by_index: dict[int, str] = {}
    for ln in lines:
        # accept "1." "1)" "1:" prefixes
        if len(ln) >= 2 and ln[0].isdigit():
            j = 0
            while j < len(ln) and ln[j].isdigit():
                j += 1
            if j < len(ln) and ln[j] in ".):":
                try:
                    idx = int(ln[:j])
                except ValueError:
                    continue
                by_index[idx] = ln[j + 1 :].strip()
    if by_index:
        return [by_index.get(i + 1, "") for i in range(expected)]
    # fallback: one line per post
    out = lines[:expected]
    while len(out) < expected:
        out.append("")
    return out


def _log_memory_event(agent_id: str, kind: str, content: str, metadata: dict) -> None:
    """Append to the SQLite audit log. Best-effort; failures are non-fatal."""
    from synthaudience.db import MemoryEventRow, get_session_factory

    try:
        factory = get_session_factory()
        with factory() as session:
            session.add(
                MemoryEventRow(
                    agent_id=agent_id,
                    kind=kind,
                    content=content,
                    metadata_json=json.dumps(metadata),
                )
            )
            session.commit()
    except Exception as e:
        logger.warning("Memory audit-log write failed for agent %s: %s", agent_id, e)
