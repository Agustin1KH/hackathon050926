"""Anonymous Reddit JSON fetcher: parse, filter by ts, degrade gracefully on errors."""

from __future__ import annotations

import time

import httpx

from synthaudience.discovery import reddit


def _listing(children: list[dict]) -> dict:
    return {"kind": "Listing", "data": {"children": children}}


def _post_child(
    pid: str,
    title: str,
    selftext: str = "",
    score: int = 10,
    created_utc: float | None = None,
    subreddit: str = "powerlifting",
) -> dict:
    return {
        "kind": "t3",
        "data": {
            "id": pid,
            "title": title,
            "selftext": selftext,
            "score": score,
            "created_utc": created_utc if created_utc is not None else time.time(),
            "permalink": f"/r/{subreddit}/comments/{pid}",
            "subreddit": subreddit,
        },
    }


class _StubResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "boom", request=httpx.Request("GET", "https://x"), response=None
            )


def test_fetch_top_posts_parses_json(monkeypatch):
    captured: dict = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured.update({"url": url, "params": params, "headers": headers})
        return _StubResponse(
            _listing(
                [
                    _post_child("a1", "First post", selftext="body 1"),
                    _post_child("a2", "Second post", selftext=""),
                ]
            )
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    posts = reddit.fetch_top_posts("r/powerlifting", limit=2)

    assert len(posts) == 2
    assert posts[0].id == "a1"
    assert posts[0].title == "First post"
    assert posts[0].subreddit == "powerlifting"
    assert posts[1].selftext == ""

    # Subreddit got normalized: 'r/powerlifting' -> 'powerlifting' in the URL.
    assert "r/powerlifting/top.json" in captured["url"]
    assert captured["params"] == {"t": "day", "limit": "2"}
    # User-Agent header is set from settings (default in tests is 'synthaudience:v0.1.0')
    assert "User-Agent" in captured["headers"]
    assert captured["headers"]["User-Agent"]


def test_fetch_top_posts_filters_by_since_ts(monkeypatch):
    now = time.time()
    payload = _listing(
        [
            _post_child("new", "fresh", created_utc=now - 100),
            _post_child("old", "stale", created_utc=now - 100_000),
        ]
    )

    monkeypatch.setattr(httpx, "get", lambda *a, **kw: _StubResponse(payload))

    posts = reddit.fetch_top_posts("powerlifting", since_ts=now - 3600)
    assert [p.id for p in posts] == ["new"]


def test_fetch_top_posts_returns_empty_on_http_error(monkeypatch):
    def fake_get(*a, **kw):
        raise httpx.ConnectError("nope")

    monkeypatch.setattr(httpx, "get", fake_get)
    assert reddit.fetch_top_posts("powerlifting") == []


def test_fetch_top_posts_returns_empty_on_bad_json(monkeypatch):
    class _BadResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            raise ValueError("not json")

    monkeypatch.setattr(httpx, "get", lambda *a, **kw: _BadResponse())
    assert reddit.fetch_top_posts("powerlifting") == []


def test_fetch_top_posts_skips_non_post_children(monkeypatch):
    """Reddit listings can mix in 'more' / comment items - we only want t3 (link) posts."""
    payload = _listing(
        [
            _post_child("a1", "real post"),
            {"kind": "more", "data": {"id": "more1"}},
            {"kind": "t1", "data": {"id": "comment1"}},
        ]
    )
    monkeypatch.setattr(httpx, "get", lambda *a, **kw: _StubResponse(payload))
    posts = reddit.fetch_top_posts("powerlifting")
    assert len(posts) == 1
    assert posts[0].id == "a1"


def test_strip_subreddit_handles_prefixes():
    assert reddit._strip_subreddit("r/foo") == "foo"
    assert reddit._strip_subreddit("/r/foo") == "foo"
    assert reddit._strip_subreddit("foo") == "foo"
    assert reddit._strip_subreddit("  r/foo  ") == "foo"
