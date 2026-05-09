"""ChromaDB memory store round-trip."""

from __future__ import annotations

import uuid

from synthaudience.memory import MemoryStore


def test_memory_add_and_recall(tmp_path):
    store = MemoryStore(persist_dir=tmp_path / "chroma")
    agent = str(uuid.uuid4())

    store.add_memory(agent, "Squat depth tutorial on r/powerlifting", {"kind": "browse"})
    store.add_memory(agent, "RPE 8 deload week notes", {"kind": "browse"})
    store.add_memory(agent, "Random unrelated cooking recipe", {"kind": "browse"})

    hits = store.recall(agent, "fixing squat depth", k=2)
    assert len(hits) == 2
    # The most relevant entry should mention squat depth
    assert any("Squat depth" in h for h in hits)


def test_memory_isolated_per_agent(tmp_path):
    store = MemoryStore(persist_dir=tmp_path / "chroma")
    a = str(uuid.uuid4())
    b = str(uuid.uuid4())
    store.add_memory(a, "agent-a memory", {"kind": "browse"})
    store.add_memory(b, "agent-b memory", {"kind": "browse"})

    hits_a = store.recall(a, "memory", k=5)
    hits_b = store.recall(b, "memory", k=5)
    assert hits_a == ["agent-a memory"]
    assert hits_b == ["agent-b memory"]


def test_memory_recall_empty_collection(tmp_path):
    store = MemoryStore(persist_dir=tmp_path / "chroma")
    assert store.recall(str(uuid.uuid4()), "anything", k=5) == []
