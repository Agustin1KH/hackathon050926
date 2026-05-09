"""Prompt templates for persona generation."""

PERSONA_SYSTEM = (
    "You design realistic, diverse audience personas for a synthetic audience research tool. "
    "You write personas that read like real people from the segment described, not caricatures. "
    "You always return a single JSON object."
)

PERSONA_USER_TEMPLATE = """Create one persona for the audience segment below.

Segment id: {segment_id}
Demographics: {demographics}
Psychographics: {psychographics}
Subreddits/interests: {interests}
Vocabulary examples (for tone calibration):
{vocabulary_block}

Constraints:
- Pick a plausible age inside the demographic age range.
- Country must match the demographic country (resolve "EU" to a specific European country).
- Occupation should be coherent with the segment's lifestyle.
- Bio: 2-3 sentences in third person, concrete and specific.
- tone_examples: 3 short snippets that sound like THIS persona, calibrated against the segment vocabulary.
- interest_graph: 3-6 subreddits (start with the segment subreddits, add 1-2 plausible adjacent ones).
- posting_ratio: a float in [0, 1] reflecting how often they comment vs. lurk.

Return strictly:
{{
  "display_name": "...",
  "age": <int>,
  "country": "...",
  "occupation": "...",
  "bio": "...",
  "tone_examples": ["...", "...", "..."],
  "interest_graph": ["r/...", "r/..."],
  "posting_ratio": <float>
}}
"""


def render_persona_prompt(segment) -> str:
    vocab_block = "\n".join(f"- {v}" for v in segment.vocabulary_examples)
    return PERSONA_USER_TEMPLATE.format(
        segment_id=segment.id,
        demographics=segment.demographics,
        psychographics=segment.psychographics,
        interests=segment.interests,
        vocabulary_block=vocab_block,
    )
