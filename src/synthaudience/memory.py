"""Per-agent persistent vector memory backed by ChromaDB."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any

from synthaudience.config import get_settings

logger = logging.getLogger(__name__)


def _safe_collection_name(agent_id: str) -> str:
    """Chroma collection names must match ^[a-zA-Z0-9._-]{3,512}$."""
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", agent_id)
    return f"agent_{cleaned}"


# Cap kept in sync with spec line 135.
MEMORY_CAP = 500


class MemoryStore:
    """Thin wrapper around chromadb's PersistentClient. One collection per agent."""

    def __init__(self, persist_dir: str | Path | None = None):
        import chromadb

        settings = get_settings()
        path = Path(persist_dir or settings.chroma_persist_dir)
        path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(path))

    def _collection(self, agent_id: str):
        name = _safe_collection_name(agent_id)
        return self._client.get_or_create_collection(name=name)

    def add_memory(self, agent_id: str, text: str, metadata: dict | None = None) -> str:
        col = self._collection(agent_id)
        mem_id = str(uuid.uuid4())
        col.add(ids=[mem_id], documents=[text], metadatas=[_clean_meta(metadata)])
        self._enforce_cap(col)
        return mem_id

    def recall(self, agent_id: str, query: str, k: int = 10) -> list[str]:
        col = self._collection(agent_id)
        try:
            count = col.count()
        except Exception as e:  # collection may have been freshly created
            logger.debug("Collection count failed for %s: %s", agent_id, e)
            count = 0
        if count == 0:
            return []
        try:
            res = col.query(query_texts=[query], n_results=min(k, count))
        except Exception as e:
            logger.warning("Memory query failed for %s: %s", agent_id, e)
            return []
        docs_per_query = res.get("documents") or [[]]
        return [d for d in docs_per_query[0] if d]

    def count(self, agent_id: str) -> int:
        try:
            return int(self._collection(agent_id).count())
        except Exception:
            return 0

    def _enforce_cap(self, col) -> None:
        try:
            n = col.count()
        except Exception:
            return
        if n <= MEMORY_CAP:
            return
        # Drop the oldest by createds-recorded order. Chroma doesn't expose
        # insertion order directly, so we sort by metadata `ts` if present.
        try:
            data = col.get(include=["metadatas"])
        except Exception as e:
            logger.warning("Memory pruning fetch failed: %s", e)
            return
        ids = data.get("ids") or []
        metas = data.get("metadatas") or []
        pairs = list(zip(ids, metas))
        pairs.sort(key=lambda p: (p[1] or {}).get("ts", ""))
        to_drop = [pid for pid, _ in pairs[: n - MEMORY_CAP]]
        if to_drop:
            try:
                col.delete(ids=to_drop)
            except Exception as e:
                logger.warning("Memory pruning delete failed: %s", e)


def _clean_meta(metadata: dict | None) -> dict:
    """Chroma requires metadata values to be str/int/float/bool. Coerce or drop."""
    if not metadata:
        return {"_": ""}  # Chroma rejects empty metadata dicts; insert a placeholder
    out: dict[str, Any] = {}
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[str(k)] = v
        else:
            out[str(k)] = str(v)
    return out or {"_": ""}
