"""Video ingestion: sample frames, ask the vision LLM to describe what happens.

The output is a single text description that drops into ContentPayload.media_description,
so the existing agent.evaluate() pipeline keeps working unchanged. One vision call per
video, regardless of how many agents end up reacting to it.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

from synthaudience.llm import LLMClient

logger = logging.getLogger(__name__)


VIDEO_DESCRIBE_SYSTEM = (
    "You are a video annotator for a synthetic-audience research tool. You watch a short "
    "video (sampled as evenly-spaced frames) and write a rich, neutral description of what "
    "happens in it. Audience-research agents read your description and react to it AS IF "
    "they had watched the video themselves, so include everything that would shape a "
    "viewer's reaction: subject and setting, what the subject is doing, on-screen text or "
    "overlays, visible props/equipment, lighting and production quality, framing, and any "
    "obvious emotional tone. Do not editorialize on whether the content is good or bad - "
    "stay descriptive."
)


VIDEO_DESCRIBE_USER = """The frames below are sampled in chronological order from a {duration_str} video titled "{title}".

Write a description that covers:
1. Setting and subject (1-2 sentences)
2. What happens across the frames in sequence (2-4 sentences)
3. On-screen text or graphical overlays, if any (verbatim)
4. Production cues: lighting, framing, apparent quality, music/audio if inferable from visuals
5. Any context that would matter to a typical viewer of this kind of content

Aim for 100-200 words. Plain prose, no bullet list in the output."""


def extract_frames(video_path: str | Path, n_frames: int = 6, max_side: int = 768) -> list[bytes]:
    """Return n_frames evenly spaced JPEG-encoded frames from the video.

    Resized so the longest side is at most max_side pixels (Anthropic's vision endpoint
    auto-downscales anyway, but smaller bytes = faster upload, lower cost).
    """
    import imageio.v3 as iio
    from PIL import Image

    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(str(path))

    # Iterate the whole stream once. For sub-20s clips this is trivial; for longer
    # clips we'd want a seek-based approach but the MVP only targets short videos.
    frames = list(iio.imiter(str(path)))
    if not frames:
        return []

    if len(frames) <= n_frames:
        chosen = frames
    else:
        step = (len(frames) - 1) / (n_frames - 1) if n_frames > 1 else 0
        indices = [int(round(i * step)) for i in range(n_frames)]
        chosen = [frames[i] for i in indices]

    out: list[bytes] = []
    for arr in chosen:
        img = Image.fromarray(arr)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        out.append(buf.getvalue())
    return out


def probe_duration(video_path: str | Path) -> float | None:
    """Best-effort duration in seconds. Returns None if we can't read it."""
    import imageio.v3 as iio

    try:
        meta = iio.immeta(str(video_path))
    except Exception as e:
        logger.debug("duration probe failed: %s", e)
        return None
    dur = meta.get("duration")
    if dur:
        try:
            return float(dur)
        except (TypeError, ValueError):
            return None
    fps = meta.get("fps")
    n = meta.get("nframes")
    if fps and n and n != float("inf"):
        try:
            return float(n) / float(fps)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    return None


async def describe_video(
    video_path: str | Path,
    title: str,
    llm: LLMClient,
    n_frames: int = 6,
    model: str | None = None,
) -> str:
    """One vision call -> rich description that downstream agents react to."""
    frames = extract_frames(video_path, n_frames=n_frames)
    if not frames:
        raise ValueError("Could not extract any frames from the video")

    duration = probe_duration(video_path)
    if duration is None:
        duration_str = "short"
    else:
        duration_str = f"{duration:.1f}-second"

    user = VIDEO_DESCRIBE_USER.format(
        duration_str=duration_str, title=title.strip() or "(untitled)"
    )
    description = await llm.complete_vision(
        system=VIDEO_DESCRIBE_SYSTEM,
        user=user,
        images=frames,
        model=model,
    )
    return description.strip()
