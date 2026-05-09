"""Convert a free-form audience description into a validated AudienceSpec.

Lets users say "100 people, half American tennis players, half European soccer players"
and get back a fully-populated AudienceSpec ready for persona generation. Same
retry-once / give-up-on-second-failure pattern as the persona generator.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from synthaudience.llm import LLMClient
from synthaudience.models import AudienceSpec

logger = logging.getLogger(__name__)


SPEC_SYSTEM = (
    "You are an audience-research analyst. Given a free-form description of a creator's "
    "audience, you produce a structured AudienceSpec for a synthetic-audience tool. "
    "Use whatever signal is in the description: rough demographics, niche interests, "
    "vocabulary samples, follower comments, geo splits. Make reasonable, specific "
    "guesses where the user was vague (real personas need concrete demographics). "
    "Return only a JSON object."
)


SPEC_USER_TEMPLATE = """User's description of the audience:
\"\"\"
{description}
\"\"\"

Target population size: {total_agents} agents.

Build an AudienceSpec with the following shape:

{{
  "name": "<short_slug-style name, lowercase, hyphens, e.g. 'tennis-soccer-creator'>",
  "total_agents": {total_agents},
  "segments": [
    {{
      "id": "<short_snake_case_id>",
      "weight": <float, all weights must sum to ~1.0>,
      "demographics": {{
        "country": "<country name or region code>",
        "age_range": [<min_age>, <max_age>],
        "gender_dist": {{"male": <float>, "female": <float>}},
        "language": "<ISO code or short>"
      }},
      "psychographics": {{
        "values": ["<3-5 short value phrases>"],
        "motivations": ["<3-5 motivations this segment has>"]
      }},
      "interests": ["<2-4 real subreddits like r/tennis, no leading slash>"],
      "vocabulary_examples": [
        "<5 short snippets that sound like real comments from people in this segment>"
      ]
    }},
    ...
  ]
}}

Rules:
- 2-4 segments unless the description clearly implies more.
- Segment weights MUST sum to 1.0 (use round numbers like 0.5/0.5 or 0.33/0.33/0.34).
- Subreddits must be real, well-trafficked communities relevant to the segment - do not invent names.
- Vocabulary examples must be in English (or whatever the segment's language is) and read like
  authentic, off-the-cuff comments - not marketing copy.
- If the description is sparse, use sensible defaults; don't refuse.
"""


SPEC_JSON_SCHEMA = {
    "type": "object",
    "required": ["name", "total_agents", "segments"],
    "properties": {
        "name": {"type": "string"},
        "total_agents": {"type": "integer", "minimum": 1},
        "segments": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": [
                    "id",
                    "weight",
                    "demographics",
                    "psychographics",
                    "interests",
                    "vocabulary_examples",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "weight": {"type": "number"},
                    "demographics": {"type": "object"},
                    "psychographics": {"type": "object"},
                    "interests": {"type": "array", "items": {"type": "string"}},
                    "vocabulary_examples": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    return s or "audience"


def _normalize_weights(spec_dict: dict[str, Any]) -> dict[str, Any]:
    """Force weights to sum to exactly 1.0 by scaling — protects against LLM rounding drift."""
    segments = spec_dict.get("segments", [])
    total = sum(float(s.get("weight", 0)) for s in segments)
    if total <= 0:
        # equal split if everything was zero
        for s in segments:
            s["weight"] = 1.0 / len(segments)
        return spec_dict
    for s in segments:
        s["weight"] = float(s["weight"]) / total
    return spec_dict


async def text_to_audience_spec(
    description: str,
    llm: LLMClient,
    total_agents: int = 12,
) -> AudienceSpec | None:
    """Run the text -> AudienceSpec parser. Retries once on validation failure."""
    if not description.strip():
        return None

    user = SPEC_USER_TEMPLATE.format(description=description.strip(), total_agents=total_agents)

    for attempt in range(2):
        try:
            data = await llm.complete(
                system=SPEC_SYSTEM,
                user=user,
                json_schema=SPEC_JSON_SCHEMA,
            )
            if isinstance(data, str):
                data = json.loads(data)

            data["name"] = _slug(str(data.get("name") or "audience"))
            data["total_agents"] = total_agents  # always honor the caller's choice
            data = _normalize_weights(data)

            return AudienceSpec(**data)
        except (ValidationError, json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
            logger.warning("AudienceSpec parsing failed (attempt %d): %s", attempt + 1, e)
            user = (
                f"{SPEC_USER_TEMPLATE.format(description=description.strip(), total_agents=total_agents)}\n\n"
                f"Your previous response failed validation: {e}. Return a corrected JSON object."
            )

    logger.error("text_to_audience_spec gave up after 2 attempts")
    return None
