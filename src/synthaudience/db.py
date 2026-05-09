"""SQLAlchemy setup and table definitions."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from synthaudience.config import get_settings


class Base(DeclarativeBase):
    pass


class AudienceRow(Base):
    __tablename__ = "audiences"

    name = Column(String, primary_key=True)
    spec_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PersonaRow(Base):
    __tablename__ = "personas"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    audience_name = Column(String, nullable=False, index=True)
    segment_id = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    country = Column(String, nullable=False)
    occupation = Column(String, nullable=False)
    bio = Column(Text, nullable=False)
    tone_examples = Column(Text, nullable=False)  # JSON list
    interest_graph = Column(Text, nullable=False)  # JSON list
    posting_ratio = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RunRow(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id = Column(String, nullable=False)
    content_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    report_json = Column(Text, nullable=True)


class ScoreRow(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=False)
    content_id = Column(String, nullable=False)
    like_score = Column(Integer, nullable=False)
    engage_probability = Column(Float, nullable=False)
    share_probability = Column(Float, nullable=False)
    sentiment = Column(String, nullable=False)
    comment = Column(Text, nullable=False)
    suggestion = Column(Text, nullable=False)
    raw_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MemoryEventRow(Base):
    __tablename__ = "memory_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, nullable=False, index=True)
    kind = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


_engine = None
_SessionLocal = None


def get_engine(database_url: str | None = None):
    global _engine
    if _engine is None:
        url = database_url or get_settings().database_url
        _engine = create_engine(url, echo=False)
    return _engine


def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(database_url))
    return _SessionLocal


def init_db(database_url: str | None = None):
    """Create all tables."""
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)


def reset_engine():
    """Reset cached engine/session (for tests)."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
