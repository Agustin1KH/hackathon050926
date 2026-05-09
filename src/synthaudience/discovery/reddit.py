"""Public-JSON Reddit fetcher. No account, no API key, no PRAW.

Reddit serves a JSON view of every public listing if you append `.json` to the URL.
We hit `https://www.reddit.com/r/<sub>/top.json?t=day&limit=N` with a descriptive
User-Agent header; that's the only requirement for low-volume anonymous access.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

import httpx

from synthaudience.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RedditPost:
    id: str
    title: str
    selftext: str
    score: int
    created_utc: float
    permalink: str
    subreddit: str


def _strip_subreddit(name: str) -> str:
    """Accept 'r/foo', '/r/foo', or 'foo' and return 'foo'."""
    s = name.strip().lstrip("/")
    if s.startswith("r/"):
        s = s[2:]
    return s


def fetch_top_posts(
    subreddit: str,
    since_ts: float | None = None,
    limit: int = 5,
    timeout: float = 10.0,
) -> List[RedditPost]:
    """Fetch top posts of the last day. `since_ts` (epoch seconds) filters older posts.

    Anonymous endpoint - no auth required, just a polite User-Agent. Returns an
    empty list on any HTTP / parse error so the browse loop degrades gracefully.
    """
    sub_name = _strip_subreddit(subreddit)
    settings = get_settings()
    url = f"https://www.reddit.com/r/{sub_name}/top.json"
    params = {"t": "day", "limit": str(limit)}
    headers = {"User-Agent": settings.reddit_user_agent}

    try:
        resp = httpx.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Reddit fetch failed for %s: %s", sub_name, e)
        return []

    children = payload.get("data", {}).get("children", [])
    posts: list[RedditPost] = []
    for child in children:
        if child.get("kind") != "t3":
            continue
        data = child.get("data") or {}
        try:
            created = float(data.get("created_utc", 0))
        except (TypeError, ValueError):
            continue
        if since_ts is not None and created < since_ts:
            continue
        posts.append(
            RedditPost(
                id=str(data.get("id", "")),
                title=data.get("title") or "",
                selftext=data.get("selftext") or "",
                score=int(data.get("score") or 0),
                created_utc=created,
                permalink=data.get("permalink") or "",
                subreddit=sub_name,
            )
        )
    return posts
