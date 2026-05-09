"""Pydantic models for all data crossing boundaries."""

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class Segment(BaseModel):
    id: str
    weight: float
    demographics: dict
    psychographics: dict
    interests: list[str]
    vocabulary_examples: list[str]


class AudienceSpec(BaseModel):
    name: str
    segments: list[Segment]
    total_agents: int = 12


class Persona(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    segment_id: str
    display_name: str
    age: int
    country: str
    occupation: str
    bio: str
    tone_examples: list[str]
    interest_graph: list[str]
    posting_ratio: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContentPayload(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    kind: Literal["instagram_post", "video_script", "ad_copy", "video"]
    title: str
    body: str
    media_description: str | None = None


class AgentScore(BaseModel):
    agent_id: uuid.UUID
    content_id: uuid.UUID
    like_score: int = Field(ge=0, le=10)
    engage_probability: float = Field(ge=0.0, le=1.0)
    share_probability: float = Field(ge=0.0, le=1.0)
    sentiment: Literal["positive", "neutral", "negative"]
    comment: str = Field(max_length=280)
    suggestion: str
    raw_json: dict = Field(default_factory=dict)


class EvaluationReport(BaseModel):
    run_id: uuid.UUID
    content_id: uuid.UUID
    overall: dict
    by_segment: dict[str, dict]
    top_themes_positive: list[str]
    top_themes_negative: list[str]
    representative_comments: list[dict]
