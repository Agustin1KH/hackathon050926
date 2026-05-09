"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from synthaudience import db as db_module


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the DB at a fresh sqlite file inside tmp_path."""
    url = f"sqlite:///{tmp_path}/test.db"
    monkeypatch.setenv("DATABASE_URL", url)

    # reset cached engine and rebuild against the new URL
    db_module.reset_engine()
    db_module.init_db(url)
    yield url
    db_module.reset_engine()


@pytest.fixture
def fitness_spec():
    from synthaudience.models import AudienceSpec

    spec_path = Path(__file__).resolve().parent.parent / "examples" / "audience_spec.json"
    return AudienceSpec(**json.loads(spec_path.read_text()))


@pytest.fixture
def sample_content():
    from synthaudience.models import ContentPayload

    content_path = Path(__file__).resolve().parent.parent / "examples" / "content_to_test.json"
    return ContentPayload(**json.loads(content_path.read_text()))
