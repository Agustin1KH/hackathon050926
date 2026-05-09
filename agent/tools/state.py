"""Supabase state tools — read/write shared DB tables.

These tools are how the agent persists drafts, mentions, and queue state.
The Next.js dashboard reads/writes the same tables, so any change here is
visible in the web UI immediately.

Owner: P1 (platform). P2 and P3 import these.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import ara_sdk as ara
from supabase import Client, create_client


def _client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


# --- Drafts ------------------------------------------------------------------

@ara.tool
def save_draft(topic: str, content: str, variant_index: int = 0) -> dict[str, Any]:
    """Persist a generated draft so it can be picked, edited, or scheduled later."""
    db = _client()
    row = db.table("drafts").insert({
        "topic": topic,
        "content": content,
        "variant_index": variant_index,
    }).execute()
    return row.data[0]


# --- Scheduled posts ---------------------------------------------------------

@ara.tool
def schedule_post(content: str, scheduled_for_iso: str, draft_id: str | None = None) -> dict[str, Any]:
    """Add a post to the scheduled queue. Defaults to status='pending' (awaits approval)."""
    db = _client()
    row = db.table("scheduled").insert({
        "content": content,
        "scheduled_for": scheduled_for_iso,
        "draft_id": draft_id,
        "status": "pending",
    }).execute()
    return row.data[0]


@ara.tool
def list_due_posts() -> list[dict[str, Any]]:
    """Return approved posts whose scheduled_for is in the past — ready to fire."""
    db = _client()
    now = datetime.utcnow().isoformat()
    res = (
        db.table("scheduled")
        .select("*")
        .eq("status", "approved")
        .lte("scheduled_for", now)
        .execute()
    )
    return res.data


@ara.tool
def list_pending_posts() -> list[dict[str, Any]]:
    """Posts queued but not yet approved (waiting for Y/N from user)."""
    db = _client()
    res = db.table("scheduled").select("*").eq("status", "pending").execute()
    return res.data


@ara.tool
def mark_post_sent(scheduled_id: str, x_tweet_id: str, content: str) -> dict[str, Any]:
    """Flip status to 'sent' and append to sent_log."""
    db = _client()
    db.table("scheduled").update({"status": "sent"}).eq("id", scheduled_id).execute()
    row = db.table("sent_log").insert({
        "x_tweet_id": x_tweet_id,
        "content": content,
    }).execute()
    return row.data[0]


@ara.tool
def mark_post_failed(scheduled_id: str) -> None:
    db = _client()
    db.table("scheduled").update({"status": "failed"}).eq("id", scheduled_id).execute()


# --- Mentions ----------------------------------------------------------------

@ara.tool
def upsert_mention(x_id: str, author: str, text: str) -> dict[str, Any] | None:
    """Insert a mention if we haven't seen it. Returns the row if newly inserted, else None."""
    db = _client()
    existing = db.table("mentions").select("id").eq("x_id", x_id).execute()
    if existing.data:
        return None
    row = db.table("mentions").insert({
        "x_id": x_id,
        "author": author,
        "text": text,
    }).execute()
    return row.data[0]


@ara.tool
def list_new_mentions() -> list[dict[str, Any]]:
    db = _client()
    res = db.table("mentions").select("*").eq("status", "new").execute()
    return res.data


@ara.tool
def mark_mention(mention_id: str, status: str) -> None:
    """status ∈ {drafted, approved, replied, skipped, spam}"""
    db = _client()
    db.table("mentions").update({"status": status}).eq("id", mention_id).execute()


# --- Replies -----------------------------------------------------------------

@ara.tool
def save_reply_draft(mention_id: str, draft_content: str) -> dict[str, Any]:
    db = _client()
    row = db.table("replies").insert({
        "mention_id": mention_id,
        "draft_content": draft_content,
    }).execute()
    return row.data[0]


@ara.tool
def list_approved_replies() -> list[dict[str, Any]]:
    """Replies the user has approved — ready to post."""
    db = _client()
    res = db.table("replies").select("*, mentions(x_id)").eq("status", "approved").execute()
    return res.data


@ara.tool
def mark_reply_sent(reply_id: str) -> None:
    db = _client()
    db.table("replies").update({"status": "sent"}).eq("id", reply_id).execute()


# --- Config ------------------------------------------------------------------

@ara.tool
def get_config(key: str) -> str | None:
    db = _client()
    res = db.table("config").select("value").eq("key", key).execute()
    return res.data[0]["value"] if res.data else None
