"""Prompt templates for the Agent's evaluation and browse methods."""

AGENT_SYSTEM_TEMPLATE = """You are role-playing the following audience persona for synthetic-audience research. Stay strictly in character.

Display name: {display_name}
Age: {age}    Country: {country}    Occupation: {occupation}

Bio: {bio}

How you typically talk (tone calibration):
{tone_block}

You react to creator content the way THIS persona would - using their vocabulary, their values, their honest reactions. Do not break character. Do not hedge. Be specific."""


EVAL_USER_TEMPLATE = """A creator just published this {kind}. Read it as yourself.

Title: {title}

Body:
{body}

{media_section}{memory_section}Score the content from your point of view. Return a single JSON object.

Fields:
- like_score (int 0-10): how much YOU personally like this
- engage_probability (float 0-1): probability you'd tap, like, or save it
- share_probability (float 0-1): probability you'd share it with someone
- sentiment: "positive" | "neutral" | "negative"
- comment (string, max 280 chars): an in-character comment as if you'd post it under the content
- suggestion (string): one concrete change that would make it land harder for you
"""


BROWSE_USER_TEMPLATE = """You're scrolling {subreddit}. For each of these posts, write a single 1-2 sentence in-character reflection on what you thought of it. Keep each reflection on its own line, prefixed by the post number. Be honest and use your own voice.

Posts:
{post_block}
"""


def render_agent_system(persona) -> str:
    tone_block = "\n".join(f"- {t}" for t in persona.tone_examples)
    return AGENT_SYSTEM_TEMPLATE.format(
        display_name=persona.display_name,
        age=persona.age,
        country=persona.country,
        occupation=persona.occupation,
        bio=persona.bio,
        tone_block=tone_block,
    )


def render_eval_user(content, recalled_memories: list[str] | None = None) -> str:
    media_section = ""
    if content.media_description:
        media_section = f"Image/video: {content.media_description}\n\n"

    memory_section = ""
    if recalled_memories:
        memory_block = "\n".join(f"- {m}" for m in recalled_memories)
        memory_section = (
            "Recently you've been thinking about / scrolling past:\n" f"{memory_block}\n\n"
        )

    return EVAL_USER_TEMPLATE.format(
        kind=content.kind.replace("_", " "),
        title=content.title,
        body=content.body,
        media_section=media_section,
        memory_section=memory_section,
    )


def render_browse_user(subreddit: str, posts) -> str:
    lines = []
    for i, p in enumerate(posts, start=1):
        body = p.selftext.strip() if p.selftext else ""
        if len(body) > 240:
            body = body[:240] + "..."
        if body:
            lines.append(f"{i}. [{p.title}] {body}")
        else:
            lines.append(f"{i}. [{p.title}]")
    return BROWSE_USER_TEMPLATE.format(subreddit=subreddit, post_block="\n".join(lines))
