# synthaudience

Synthetic Audience Agent Network — MVP. Creators upload content (an Instagram caption + image, a video script, an ad draft), and a population of persona-bound LLM agents reads it, scores it, and explains what they liked or didn't. Each agent has a persistent memory and periodically browses Reddit to stay in touch with its segment's culture.

## Setup

Requires Python 3.11+ and [`uv`](https://github.com/astral-sh/uv).

```bash
uv sync
cp .env.example .env       # then fill in your API keys
synthaudience init
```

`synthaudience init` creates `data/synthaudience.db` (SQLite) and `data/chroma/` (vector store).

## Environment variables

All loaded from `.env` via `pydantic-settings`. See `.env.example`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `ANTHROPIC_API_KEY` | _(empty)_ | Required for the default provider |
| `OPENAI_API_KEY` | _(empty)_ | Required when `LLM_PROVIDER=openai` |
| `BROWSE_MODEL` | `claude-haiku-4-5-20251001` | Cheap model for the discovery loop |
| `EVAL_MODEL` | `claude-sonnet-4-6` | Stronger model for content evaluation |
| `REDDIT_USER_AGENT` | `synthaudience:v0.1.0` | Sent on every Reddit request (no API key needed - we hit the public JSON endpoint) |
| `DISCOVERY_INTERVAL_MINUTES` | `60` | APScheduler tick for the browse loop. Lower for fresher memories; safe down to ~15 minutes for a 12-agent population. |
| `DATABASE_URL` | `sqlite:///data/synthaudience.db` | Override for tests / external Postgres |
| `CHROMA_PERSIST_DIR` | `data/chroma` | Where Chroma writes its files |

## CLI

The `synthaudience` entrypoint is installed by `uv sync`.

```bash
# 1. Generate a population of personas from an audience spec
synthaudience generate-personas examples/audience_spec.json

# 2. (Optional) seed agent memories by browsing Reddit once
synthaudience browse-once

# 3. Score a piece of content with the full population
synthaudience evaluate examples/content_to_test.json --out report.json

# 4. Pretty-print a previously generated report
synthaudience report <run_id>
```

`generate-personas` is idempotent against the audience name in the spec — re-running it only fills any segment shortfall instead of regenerating personas that already exist.

## HTTP API

Run with `uv run uvicorn synthaudience.api:app --reload`.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/audience` | Persist an `AudienceSpec` |
| `POST` | `/personas/generate` | Body `{audience_id}` — generate personas for a stored spec |
| `POST` | `/browse/run-once` | Run one discovery pass |
| `POST` | `/evaluate` | Body: `ContentPayload` — synchronous evaluation, returns `{run_id}` |
| `GET` | `/reports/{run_id}` | Aggregated `EvaluationReport` |
| `GET` | `/personas?segment_id=` | List personas, optionally filtered |

## Architecture

```
     AudienceSpec (JSON)
            │
            ▼
   ┌──────────────────┐         ┌─────────────────────┐
   │ persona generator│────────▶│ SQLite: personas    │
   │ (largest-rem.)   │         │  + audiences        │
   └──────────────────┘         └─────────────────────┘
                                          │
                                          ▼
   ┌──────────────────┐         ┌─────────────────────┐
   │ Reddit (PRAW)    │────────▶│ Agent.browse()      │──┐
   └──────────────────┘         │ (cheap model)       │  │
                                └─────────────────────┘  │
                                                         ▼
                                          ┌─────────────────────┐
                                          │ Chroma: per-agent   │
                                          │ vector memory       │
                                          └─────────────────────┘
                                                         ▲
                                                         │ recall(top-k)
            ContentPayload (JSON)                        │
                    │                                    │
                    ▼                                    │
   ┌─────────────────────────────────────────────────────┴──┐
   │ runner: asyncio.gather + Semaphore(8) over all agents  │
   │   Agent.evaluate() ─▶ AgentScore (strong model)        │
   └────────────────────────────────────────────────────────┘
                    │
                    ▼
   ┌─────────────────────────┐         ┌─────────────────────┐
   │ aggregator: per-segment │────────▶│ EvaluationReport    │
   │ means + theme clusters  │         │ (SQLite + JSON)     │
   └─────────────────────────┘         └─────────────────────┘
```

Memory is intentionally double-tracked: ChromaDB is the vector index used for recall during evaluation, while SQLite's `memory_events` table is a durable, human-readable audit log of every browse reflection.

## Tests

```bash
# On machines with system-installed pytest plugins (e.g. ROS), disable autoload:
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest -p pytest_asyncio.plugin

# Otherwise:
uv run pytest

# Live API smoke test (hits Anthropic for one persona):
RUN_LIVE_LLM=1 uv run pytest tests/test_live_llm.py
```

## Things this MVP intentionally does not do

- No web UI, no auth, no multi-tenancy.
- No agent-to-agent interaction — every agent evaluates content independently.
- No Letta/LangGraph/CrewAI — agents are plain Python classes.
- No streaming — every LLM call returns JSON validated against a schema, with one retry on failure.
- No Postgres, no Celery, no Redis — SQLite + Chroma + APScheduler in-process.

`# TODO(v2):` markers throughout the source flag where these constraints get lifted later.
