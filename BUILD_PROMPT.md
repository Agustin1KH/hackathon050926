# Build Spec — Synthetic Audience Agent Network (MVP)

You are building the first working MVP of a synthetic audience system. Creators upload content (an Instagram caption + image, a video script, an ad draft), and a population of persona-bound LLM agents — each modeled after a real audience segment — reads it, scores it, and explains what they liked or didn't. Each agent maintains a persistent memory and periodically browses Reddit so its preferences stay current with its segment's culture.

This MVP must run end-to-end on a laptop with `docker compose up` and a few CLI commands. Optimize for clarity over features. No auth, no UI, no production hardening — just a CLI + FastAPI surface that proves the loop works.

---

## Tech stack (pin these — don't substitute)

- **Python 3.11+**, `uv` for dependency management, `ruff` + `black` for lint/format
- **FastAPI** for the HTTP API
- **SQLite** (via SQLAlchemy 2.x) for personas / runs / scores — keep it file-based for the MVP
- **ChromaDB** (local persistent mode) for per-agent archival memory
- **Anthropic SDK** (`anthropic`) as the primary LLM client; support an `LLM_PROVIDER=openai` fallback that uses `openai`. Default model: `claude-haiku-4-5-20251001` for browsing, `claude-sonnet-4-6` for evaluation. Read keys from `.env` via `pydantic-settings`.
- **PRAW** for Reddit access (read-only mode is fine — no OAuth user flow)
- **APScheduler** (in-process) for the discovery cron — no Redis, no Celery in MVP
- **Pydantic v2** for every data model that crosses a boundary
- **pytest** + **pytest-asyncio** for tests
- **Rich** for nice CLI output

Do not pull in Letta, LangGraph, CrewAI, or AutoGen for the MVP. We'll layer those in v2 — for now, agents are plain Python classes that hold a persona, a memory handle, and an LLM client.

---

## Repo layout

```
synthaudience/
├── pyproject.toml
├── README.md
├── .env.example
├── docker-compose.yml          # only needed if we add Postgres later; include a stub
├── data/                       # sqlite + chroma persisted here, gitignored
├── examples/
│   ├── audience_spec.json      # the fitness-influencer example below
│   └── content_to_test.json    # sample IG post payload
├── src/synthaudience/
│   ├── __init__.py
│   ├── config.py               # pydantic-settings, loads .env
│   ├── models.py               # Pydantic models: AudienceSpec, Segment, Persona, ContentPayload, AgentScore, EvaluationReport
│   ├── db.py                   # SQLAlchemy setup, tables: personas, runs, scores, memory_events
│   ├── llm.py                  # thin wrapper: complete(system, user, model, json_schema=None) -> str|dict
│   ├── memory.py               # ChromaDB wrapper, one collection per agent: add_memory, recall(query, k)
│   ├── personas/
│   │   ├── generator.py        # AudienceSpec -> List[Persona] via stratified sampling + LLM expansion
│   │   └── prompts.py
│   ├── agents/
│   │   ├── agent.py            # Agent class: persona + memory + llm; methods: browse(), evaluate(content)
│   │   └── prompts.py          # system prompt template, browse prompt, eval prompt with JSON schema
│   ├── discovery/
│   │   ├── reddit.py           # fetch_top_posts(subreddit, since_ts, limit) -> List[Post]
│   │   └── scheduler.py        # APScheduler job: for each agent, run browse() on its top subreddit
│   ├── evaluation/
│   │   ├── runner.py           # fan out content to all agents in parallel (asyncio.gather + semaphore)
│   │   └── aggregator.py       # group scores by segment, cluster comments, build EvaluationReport
│   ├── api.py                  # FastAPI app: POST /audience, POST /personas/generate, POST /evaluate, GET /reports/{id}
│   └── cli.py                  # typer-based CLI: init, generate-personas, browse-once, evaluate, report
└── tests/
    ├── test_personas.py        # generator produces correct distribution
    ├── test_agent_eval.py      # one agent evaluates content and returns valid JSON
    ├── test_aggregator.py      # known scores aggregate to expected segment averages
    └── test_e2e.py             # end-to-end: 6 agents (3 segments, 2 each) evaluate a sample post
```

---

## Data models (Pydantic)

```
AudienceSpec
  name: str
  segments: list[Segment]
  total_agents: int            # e.g. 100; for MVP default 12

Segment
  id: str                      # "us_powerlifter"
  weight: float                # must sum to 1.0 across segments
  demographics: dict           # country, age_range, gender_dist, language
  psychographics: dict         # values, motivations
  interests: list[str]         # subreddits, hashtags, creator handles
  vocabulary_examples: list[str]  # 5-10 real-style snippets to ground tone

Persona  (one per agent)
  id: uuid
  segment_id: str
  display_name: str
  age: int
  country: str
  occupation: str
  bio: str                     # 2-3 sentences
  tone_examples: list[str]
  interest_graph: list[str]    # subreddits this agent reads
  posting_ratio: float         # 0..1, how likely to comment vs lurk
  created_at: datetime

ContentPayload
  id: uuid
  kind: Literal["instagram_post", "video_script", "ad_copy"]
  title: str
  body: str                    # caption / script / copy
  media_description: str | None  # text description of image/video for MVP

AgentScore
  agent_id: uuid
  content_id: uuid
  like_score: int              # 0..10
  engage_probability: float    # 0..1, would they tap/like/save
  share_probability: float     # 0..1
  sentiment: Literal["positive","neutral","negative"]
  comment: str                 # ≤ 280 chars, in-character
  suggestion: str              # 1 concrete change
  raw_json: dict               # full LLM output for debugging

EvaluationReport
  run_id: uuid
  content_id: uuid
  overall: dict                # avg like_score, engage_prob, share_prob, sentiment_dist
  by_segment: dict[str, dict]  # same metrics per segment_id
  top_themes_positive: list[str]  # LLM-clustered themes from positive comments
  top_themes_negative: list[str]
  representative_comments: list[dict]  # {segment_id, comment} sampled per segment
```

All LLM calls that produce structured data MUST use a JSON schema and validate with Pydantic before persisting. If validation fails, retry once with the validation error appended to the prompt; on second failure, log and skip that agent for that run.

---

## Pipelines to implement

**1. Persona generation** (`personas/generator.py`)
Given an `AudienceSpec` with weights, allocate `total_agents` across segments using largest-remainder rounding (so weights = [0.25, 0.25, 0.25, 0.25] with 12 agents = 3/3/3/3 exactly). For each slot, call the LLM once with the segment's demographics/psychographics/vocabulary_examples and ask for a JSON Persona. Persist all personas to SQLite. Idempotent: running again with the same `AudienceSpec.name` regenerates only missing slots.

**2. Discovery loop** (`discovery/scheduler.py`)
APScheduler job, runs every 6 hours by default (configurable, and a `browse-once` CLI command for manual triggering). For each persona: pick one subreddit from `interest_graph` it hasn't visited recently, fetch top 5 posts of the last 24h via PRAW, and call `agent.browse(posts)`. The browse method asks the LLM (cheap model) to write a 1–2 sentence in-character reflection for each post, then writes those reflections plus the post titles into Chroma as memory entries with metadata `{kind: "browse", subreddit, post_id, ts}`. Cap memory at 500 entries per agent (drop oldest).

**3. Evaluation** (`evaluation/runner.py`)
`evaluate(content_payload, run_id)`:
- Load all personas.
- For each agent in parallel (asyncio + semaphore of size 8 to respect rate limits): pull top-10 most relevant memories via Chroma similarity to the content's title+body, build the eval prompt (persona + relevant memories + content), call the strong model with the AgentScore JSON schema.
- Persist every AgentScore to SQLite.
- Hand the full set to `aggregator.build_report(run_id)`.

**4. Aggregation** (`evaluation/aggregator.py`)
Compute overall and per-segment means. Cluster comments: bucket comments by sentiment, then ask the LLM to extract 3–5 recurring themes per bucket (one call per bucket, batched). Sample 1 representative comment per segment for the report. Persist `EvaluationReport` and return it.

---

## API surface (FastAPI)

```
POST /audience              body: AudienceSpec        -> {audience_id}
POST /personas/generate     body: {audience_id}       -> {personas: [...], count}
POST /browse/run-once                                 -> {agents_browsed, memories_added}
POST /evaluate              body: ContentPayload      -> {run_id}  (async; kicks job)
GET  /reports/{run_id}                                -> EvaluationReport
GET  /personas              ?segment_id=...           -> [Persona]
```

Make `/evaluate` synchronous in the MVP (await the runner). Async/job-queue can come later.

---

## CLI (`synthaudience` entrypoint via Typer)

```
synthaudience init                          # create db, chroma dir, copy example files
synthaudience generate-personas examples/audience_spec.json
synthaudience browse-once
synthaudience evaluate examples/content_to_test.json --out report.json
synthaudience report <run_id>               # pretty-print with rich
```

---

## Example audience spec to ship in `examples/audience_spec.json`

A fitness-influencer audience: 4 segments (US powerlifter, US bodybuilder, EU powerlifter, EU bodybuilder), each weight 0.25, `total_agents: 12`. Each segment's `interests` lists 2–3 real subreddits (e.g. `r/powerlifting`, `r/bodybuilding`, `r/naturalbodybuilding`, `r/weightroom`) and 5 short vocabulary_examples that sound like real comments from those communities.

## Example content payload in `examples/content_to_test.json`

An Instagram post: title "5 cues that fixed my squat depth", a 120-word caption, `media_description` = "Athlete in a low-bar back squat at the bottom of the rep, chalk on bar, grey gym."

---

## Acceptance criteria — the MVP is done when all pass

1. `uv sync && synthaudience init && synthaudience generate-personas examples/audience_spec.json` produces exactly 12 personas with the 3/3/3/3 distribution, all valid Pydantic models, persisted to SQLite.
2. `synthaudience browse-once` runs, hits Reddit (mock the network in tests), and adds ≥1 memory entry per agent to Chroma.
3. `synthaudience evaluate examples/content_to_test.json` returns a `run_id` in <60s on a normal laptop, with one valid `AgentScore` per agent persisted.
4. `synthaudience report <run_id>` prints overall and per-segment means, plus 3–5 themes for positive and negative buckets, plus one representative comment per segment.
5. `pytest` is green. Tests must include: persona distribution math, JSON-schema validation of one real LLM eval call (gated behind `RUN_LIVE_LLM=1`), aggregator math on fixture data, and an e2e test using a stubbed LLM client.
6. `ruff check` and `black --check` pass.
7. README explains: setup, env vars, the 4 CLI commands above, and a one-paragraph architecture overview with a small ASCII diagram of the pipeline.

---

## Build order (do it in this sequence — don't jump ahead)

1. Scaffold repo, `pyproject.toml`, `.env.example`, `config.py`, `db.py`, `models.py`. Get `synthaudience init` working.
2. Implement `llm.py` with a stubbable interface. Write a fake provider for tests.
3. Implement persona generator + its test. Verify distribution math without calling an LLM (use the fake).
4. Implement `agents/agent.py` with `evaluate()` only (skip browse for now). Write `test_agent_eval.py` with the fake LLM returning a canned JSON.
5. Implement evaluation runner + aggregator + `test_aggregator.py`.
6. Wire the FastAPI endpoints and CLI commands; write `test_e2e.py` end-to-end with the fake LLM and 6 agents across 3 segments.
7. Implement Reddit discovery + `agent.browse()` + scheduler. Mock PRAW in tests.
8. Add memory recall to the eval path (top-k Chroma query before building the eval prompt).
9. Write the README. Run all acceptance criteria. Fix anything that fails.

After every step, run the tests and commit. Do not move to the next step with red tests.

---

## Things to NOT do in this MVP

- No web UI, no auth, no multi-tenant, no rate-limit middleware.
- No Letta/LangGraph/CrewAI integration — agents are plain classes.
- No Instagram scraping — the audience spec is hand-written for now.
- No agent-to-agent interaction (echo chambers, cascades) — every agent evaluates content independently.
- No vector DB other than Chroma; no Postgres.
- No streaming responses; JSON-only with schema validation.
- No emojis in code, comments, or docs unless they appear in user-supplied content.

When in doubt, choose the smaller, more boring option and leave a `# TODO(v2):` comment with a one-line note for what to revisit later.
