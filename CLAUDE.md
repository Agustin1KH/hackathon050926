# Social Media Agent — Hackathon Build Plan

## Concept
A social media agent that manages your X (Twitter) presence — drafting posts,
scheduling them, and triaging mentions/DMs with AI-drafted replies. You approve
each action either from a **web dashboard** or by **replying Y/N to a text
message**. The agent runs 24/7 in Ara's cloud, even when your laptop is off.

---

## Architecture: Hybrid (Ara + Next.js + Supabase)

```
┌─────────────────────────┐       ┌─────────────────────────┐
│  Ara (cloud)            │       │  Next.js (local/hosted) │
│  agent.py               │◄─────►│  Dashboard / Inbox /    │
│  - cron every 15 min    │       │  Schedule / Settings    │
│  - draft / classify     │       │                         │
│  - post / reply on X    │       │                         │
│  - SMS approval prompts │       │                         │
└────────────┬────────────┘       └────────────┬────────────┘
             │                                 │
             └───────────────┬─────────────────┘
                             ▼
                ┌──────────────────────────┐
                │  Supabase (Postgres)     │
                │  drafts / mentions /     │
                │  scheduled / sent_log /  │
                │  config / tokens         │
                └──────────────────────────┘
```

**Three layers, three responsibilities:**
- **Ara** — the agent runtime. Hosts `agent.py`, runs it on cron, calls Claude,
  invokes `@ara.tool` Python functions for X API + DB writes, sends SMS via
  the `linq_send_message` connector for approval prompts.
- **Supabase** — shared state. Both Ara and the Next.js app read/write here.
  Single source of truth for drafts, queue, mentions, sent log, config.
- **Next.js** — the dashboard. Reads from Supabase to show queue/inbox; writes
  approval flags back. Built on the existing scaffold (Next.js 16 + AI SDK 6
  + shadcn).

**Approval paths (either works):**
1. Web → click ✓ on a pending draft → DB flag flips → Ara posts on next tick.
2. SMS → Ara texts draft → reply Y → Ara flips flag itself → posts.

---

## Platform Decision: X (Twitter) Only

**Why not Instagram:**
- Graph API gates DM access behind business account + Meta app review (weeks).
- Posting via API requires verified business/creator account.
- Scraping (instagrapi etc.) violates ToS; accounts get banned. Bad UX for an
  installable end-user product.

**Why X:**
- v2 API works on free/basic tier immediately.
- Reads mentions, posts, replies. (DMs require basic tier.)
- OAuth 2.0 PKCE is straightforward.

---

## Stack

| Layer | Tool | Why |
|---|---|---|
| Agent runtime | **Ara SDK** (Python) | Cloud-hosted, built-in cron, tools, SMS connector |
| Shared DB | **Supabase** (Postgres) | REST API, auth, free tier, mature Python + JS SDKs |
| Dashboard | **Next.js 16** (existing scaffold) | Already wired with AI SDK 6, shadcn, Tailwind v4 |
| X client | `tweepy` (Python) inside Ara tools | Mature, OAuth 2.0 support |
| Approval UX | Web (Next.js) **or** SMS (Ara `linq_send_message`) | Both write to the same DB flag |
| Secrets | Ara secrets for the agent; `.env.local` for Next.js | Never committed |

---

## Repo Layout

```
ara-hackathon/
├── agent/                       # Python — deployed to Ara cloud
│   ├── agent.py                 # ara.Job + system instructions
│   ├── tools/
│   │   ├── x_client.py          # @ara.tool: post_tweet, get_mentions, reply_to
│   │   ├── state.py             # @ara.tool: save_draft, list_pending, mark_*
│   │   └── approval.py          # @ara.tool: send_approval_sms
│   ├── prompts.py               # system instructions + style profile injection
│   ├── requirements.txt         # ara-sdk, tweepy, supabase
│   └── .env.example             # X creds, Supabase URL/key, phone number
│
├── app/                         # Next.js — dashboard
│   ├── page.tsx                 # dashboard home
│   ├── draft/page.tsx           # generate variants → queue
│   ├── inbox/page.tsx           # pending mentions/DMs with replies
│   ├── schedule/page.tsx        # queue table
│   ├── settings/page.tsx        # style profile, post times, X auth
│   └── api/                     # thin Next.js routes wrapping Supabase queries
│
├── lib/                         # shared TS
│   ├── supabase.ts              # Supabase client
│   └── types.ts                 # generated DB types (zod or supabase-codegen)
│
├── db/
│   └── schema.sql               # Supabase tables — single source of truth
│
└── components/                  # shadcn UI primitives + custom
```

---

## Supabase Schema (locked first hour)

```sql
create table drafts (
  id uuid primary key default gen_random_uuid(),
  topic text,
  content text not null,
  variant_index int,
  created_at timestamptz default now()
);

create table scheduled (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  scheduled_for timestamptz not null,
  status text not null default 'pending',  -- pending | approved | sent | failed
  draft_id uuid references drafts(id),
  created_at timestamptz default now()
);

create table sent_log (
  id uuid primary key default gen_random_uuid(),
  x_tweet_id text,
  content text not null,
  sent_at timestamptz default now()
);

create table mentions (
  id uuid primary key default gen_random_uuid(),
  x_id text unique not null,
  author text,
  text text,
  fetched_at timestamptz default now(),
  status text not null default 'new'        -- new | drafted | approved | replied | skipped | spam
);

create table replies (
  id uuid primary key default gen_random_uuid(),
  mention_id uuid references mentions(id),
  draft_content text not null,
  status text not null default 'pending',   -- pending | approved | sent
  created_at timestamptz default now()
);

create table config (
  key text primary key,
  value text
);
-- seeded: style_profile, post_schedule (e.g. "09:00,13:00,18:00"), phone_number
```

**Status state machines:**
- `scheduled.status`: pending → approved → sent (or → failed)
- `mentions.status`: new → drafted → approved → replied (or → skipped/spam)
- `replies.status`: pending → approved → sent

---

## Build Order (Hackathon, 6 hours, 4 people in parallel)

| Hour | P1 (Platform) | P2 (X tools) | P3 (Agent brain) | P4 (Dashboard) |
|------|---------------|--------------|------------------|----------------|
| 1    | Supabase project, schema, env wiring, agent skeleton boots | tweepy auth setup, `post_tweet` tool works | system instructions skeleton, hello-world Job | gut placeholder, dashboard route |
| 2    | `ara deploy` works end-to-end, secrets configured | `get_mentions`, `reply_to`, `send_dm` tools | drafting prompt: topic → 3 variants | /draft page UI |
| 3    | DB types codegen, shared `tools/state.py` | classify spam vs reply tool | full agent.py: tools registered, cron set | /inbox page UI |
| 4    | `linq_send_message` SMS approval flow | (integrating with state) | scheduled-post flow end-to-end | /schedule page |
| 5    | Approval flag round-trip tested | (polish) | mentions-poll flow end-to-end | /settings page |
| 6    | README, install steps, demo script | (polish) | (polish) | landing page polish |

---

## What Makes This Stand Out

- **Always-on without a server.** Ara handles 24/7 execution; you don't run a worker on your laptop.
- **Two-channel approval.** Approve from a web dashboard or by texting Y. Whichever is closer when you're notified.
- **Style-aware.** Every draft personalized via a style profile injected into the system prompt.
- **Approval-first.** Nothing posts to X without you clicking ✓ or replying Y.
- **Demo-friendly.** Live SMS approval on stage > clicking buttons in a browser.

---

## .env templates

**`agent/.env.example`** (Python — Ara secrets):
```
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_SECRET=
X_BEARER_TOKEN=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=          # service-role key for full DB access from Ara
USER_PHONE_NUMBER=             # for SMS approval
```

**`.env.local`** (Next.js):
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
AI_GATEWAY_API_KEY=            # only if dashboard does its own AI calls
AI_MODEL=anthropic/claude-sonnet-4.6
```

---

## Demo Flow (target ≤ 5 minutes)

1. Open dashboard. Show empty queue.
2. Click "New draft" → type *"thoughts on vibe coding"* → 3 variants stream in → pick one → schedule for +1 min.
3. Show the row land in `scheduled` table (Supabase live view).
4. Phone buzzes — SMS: *"Posting in 60s: '...'. Reply Y to confirm or N to cancel."*
5. Reply Y. Tweet appears live on X.
6. Trigger an inbox poll → SMS: *"@alice asked: '...'. Draft reply: '...'. Send?"*
7. Open dashboard `/inbox`, edit the reply in the browser instead, click ✓ → reply posts.

Both channels demoed, end-to-end, in under 5 minutes.

---

## Non-Goals (cut to ship)

- Bluesky / LinkedIn / Threads integration
- Instagram (any path)
- Image/video posting
- Multi-account support
- Analytics / metrics
