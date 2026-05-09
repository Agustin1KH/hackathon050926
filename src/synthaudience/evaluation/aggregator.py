"""Aggregate per-agent scores into an EvaluationReport with per-segment means and themes."""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from typing import Iterable

from synthaudience.llm import LLMClient
from synthaudience.models import AgentScore, EvaluationReport, Persona

logger = logging.getLogger(__name__)


THEMES_SYSTEM = (
    "You read short audience comments and extract the dominant themes. "
    "Return only a JSON object."
)

THEMES_USER_TEMPLATE = """The following are {sentiment} reactions to one piece of content. Extract 3-5 short, distinct themes that recur. Use noun phrases under 6 words.

Comments:
{comment_block}

Return: {{"themes": ["...", "...", "..."]}}"""

THEMES_SCHEMA = {
    "type": "object",
    "required": ["themes"],
    "properties": {
        "themes": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
    },
}


def _means(scores: Iterable[AgentScore]) -> dict:
    scores = list(scores)
    if not scores:
        return {
            "n": 0,
            "like_score": 0.0,
            "engage_probability": 0.0,
            "share_probability": 0.0,
            "sentiment_dist": {"positive": 0.0, "neutral": 0.0, "negative": 0.0},
        }
    n = len(scores)
    like = sum(s.like_score for s in scores) / n
    eng = sum(s.engage_probability for s in scores) / n
    shr = sum(s.share_probability for s in scores) / n
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for s in scores:
        counts[s.sentiment] += 1
    dist = {k: round(v / n, 4) for k, v in counts.items()}
    return {
        "n": n,
        "like_score": round(like, 4),
        "engage_probability": round(eng, 4),
        "share_probability": round(shr, 4),
        "sentiment_dist": dist,
    }


async def _extract_themes(sentiment: str, comments: list[str], llm: LLMClient) -> list[str]:
    if not comments:
        return []
    block = "\n".join(f"- {c}" for c in comments)
    user = THEMES_USER_TEMPLATE.format(sentiment=sentiment, comment_block=block)
    try:
        data = await llm.complete(system=THEMES_SYSTEM, user=user, json_schema=THEMES_SCHEMA)
        if isinstance(data, str):
            data = json.loads(data)
        themes = data.get("themes", [])
        return [str(t) for t in themes][:5]
    except Exception as e:
        logger.warning("Theme extraction failed for %s bucket: %s", sentiment, e)
        return []


async def build_report(
    run_id: uuid.UUID,
    content_id: uuid.UUID,
    scores: list[AgentScore],
    personas: list[Persona],
    llm: LLMClient,
) -> EvaluationReport:
    persona_segment = {p.id: p.segment_id for p in personas}

    by_segment_scores: dict[str, list[AgentScore]] = defaultdict(list)
    for s in scores:
        seg = persona_segment.get(s.agent_id, "unknown")
        by_segment_scores[seg].append(s)

    overall = _means(scores)
    by_segment = {seg: _means(items) for seg, items in by_segment_scores.items()}

    pos_comments = [s.comment for s in scores if s.sentiment == "positive"]
    neg_comments = [s.comment for s in scores if s.sentiment == "negative"]

    pos_themes = await _extract_themes("positive", pos_comments, llm)
    neg_themes = await _extract_themes("negative", neg_comments, llm)

    representative: list[dict] = []
    for seg, items in by_segment_scores.items():
        if items:
            # pick the one closest to the segment mean like_score
            mean = by_segment[seg]["like_score"]
            pick = min(items, key=lambda s: abs(s.like_score - mean))
            representative.append({"segment_id": seg, "comment": pick.comment})

    return EvaluationReport(
        run_id=run_id,
        content_id=content_id,
        overall=overall,
        by_segment=by_segment,
        top_themes_positive=pos_themes,
        top_themes_negative=neg_themes,
        representative_comments=representative,
    )
