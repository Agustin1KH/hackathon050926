"""X / Twitter API tools.

Owner: P2. Stubs only — fill in with tweepy.
All functions decorated with @ara.tool so the agent can call them.
"""

from __future__ import annotations

import os
from typing import Any

import ara_sdk as ara

# TODO(P2): import tweepy and build a Client at module load
# import tweepy
# def _client() -> tweepy.Client:
#     return tweepy.Client(
#         bearer_token=os.environ["X_BEARER_TOKEN"],
#         consumer_key=os.environ["X_API_KEY"],
#         consumer_secret=os.environ["X_API_SECRET"],
#         access_token=os.environ["X_ACCESS_TOKEN"],
#         access_token_secret=os.environ["X_ACCESS_SECRET"],
#     )


@ara.tool
def post_tweet(content: str) -> dict[str, Any]:
    """Post a tweet. Returns {"id": "<tweet_id>", "text": "..."}."""
    raise NotImplementedError("P2: implement with tweepy.Client.create_tweet")


@ara.tool
def reply_to(tweet_id: str, content: str) -> dict[str, Any]:
    """Reply to a tweet. Returns {"id": "<reply_id>"}."""
    raise NotImplementedError("P2: implement with tweepy.Client.create_tweet(in_reply_to_tweet_id=...)")


@ara.tool
def get_recent_mentions(since_id: str | None = None) -> list[dict[str, Any]]:
    """Return new mentions of the authenticated user.
    Each item: {"x_id", "author", "text"}.
    """
    raise NotImplementedError("P2: tweepy.Client.get_users_mentions(user.id, since_id=...)")


@ara.tool
def send_dm(recipient_id: str, content: str) -> dict[str, Any]:
    """Send a direct message. (Requires Basic tier on X.)"""
    raise NotImplementedError("P2: implement with tweepy DM endpoints")
