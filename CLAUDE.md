# Social Media Agent — Hackathon Build Plan

## Concept
A standalone social media agent that manages your X (Twitter) presence —
drafting posts, scheduling them, triaging mentions, and **analyzing your
follower audience** to tune content for who actually reads you. Approve from
a **web dashboard** or by **replying Y/N to a text**. Posting uses the
**X API v2** via `twitter-api-v2`.

**Inspired by Ara's capability set** (persistent agent, phone access, browser
automation, always-on) but built standalone — no Ara API dependency.

---

## Architecture

```
┌─────────────────────────────────────┐
│ Next.js 16 dashboard                │
│  • /draft   — Anthropic-drafted     │
│  • /approve — pending posts queue   │
│  • /inbox   — mentions + replies    │
│  • /stats   — sent log + metrics    │
│  • /settings— style profile, schedule│
└──────────────┬──────────────────────┘
               │ R/W
               ▼
┌─────────────────────────────────────┐
│ Supabase (Postgres)                 │
│  drafts / scheduled / sent_log /    │
│  mentions / replies / config        │
└──────────────┬──────────────────────┘
               │ poll
               ▼
┌─────────────────────────────────────┐
│ Worker (Node + X API (twitter-api-v2))          │
│  • node-cron tick every minute      │
│  • Approved scheduled → post via    │
│    long-lived Chrome session        │
│  • Approved replies → reply via     │
│    same session                     │
│  • Poll mentions every N min        │
│  • Optional: Twilio SMS approval    │
└─────────────────────────────────────┘
```

**Three responsibilities, three pieces:**
- **Next.js** — dashboard UI + API routes that read/write Supabase + call Anthropic for drafting.
- **Supabase** — single source of truth for all state. Both UI and worker hit it.
- **Worker** — keeps a logged-in Chrome session, polls Supabase, executes approved actions.

---

## Why X API (not browser automation)

For posting, X API and Playwright are both viable, but **for follower
analysis the X API is dramatically better**: scraping followers is fragile,
slow, and rate-limit-prone. Since this product depends on understanding the
user's audience, we standardize on the X API for everything.

Free-tier limits we work within:
- 500 posts / month (more than enough for hackathon + light real use)
- ~75 reads/15min for mentions polling (fine at our 5-min cadence)
- Followers endpoint paginates 100/page (we cap at 100 for hackathon)

Tokens: 5 values from developer.x.com → app → Keys & Tokens. Stored in
`.env.local`, never committed.

---

## Stack

| Layer | Tool | Why |
|---|---|---|
| Dashboard | **Next.js 16** + AI SDK 6 + shadcn (existing scaffold) | Already wired |
| AI | **Anthropic SDK** (`@anthropic-ai/sdk`), model `claude-sonnet-4-6` | Drafting + bio classification |
| State | **Supabase** (Postgres) | REST API, free tier, provisioned |
| X integration | **`twitter-api-v2`** | Post, reply, mentions, **followers** |
| Worker | **Node** + `node-cron` + `tsx` | Background loop, same TS as the app |
| SMS (optional) | **Twilio** | Inbound webhook → flip approval flag |

---

## Repo Layout

```
ara-hackathon/
├── app/                       # Next.js dashboard
│   ├── page.tsx               # dashboard home
│   ├── draft/page.tsx         # generate variants → save
│   ├── approve/page.tsx       # pending posts review
│   ├── inbox/page.tsx         # mentions with AI replies
│   ├── stats/page.tsx         # sent log + metrics
│   ├── settings/page.tsx      # style profile, schedule
│   └── api/
│       ├── draft/route.ts     # Anthropic draft generation
│       ├── reply/route.ts     # Anthropic reply generation
│       ├── classify/route.ts  # spam / no_action / reply_needed
│       └── twilio/route.ts    # SMS webhook → flip approval flag
│
├── worker/                    # Long-lived Node process
│   └── index.ts               # cron loop: post / reply / poll mentions
│
├── lib/
│   ├── supabase.ts            # browser/server client
│   ├── supabase-server.ts     # service-role client (server only)
│   ├── anthropic.ts           # Anthropic SDK client + prompts
│   ├── types.ts               # mirrors db/schema.sql
│   └── prompts.ts             # draft/reply/classify templates
│
├── db/
│   └── schema.sql             # Supabase schema (already written)
│
├── components/                # shadcn primitives + custom
└── package.json
```

---

## Supabase Schema

(Already in `db/schema.sql` — unchanged from H1.) Six tables:
`drafts`, `scheduled`, `sent_log`, `mentions`, `replies`, `config`.

State machines:
- `scheduled.status`: `pending → approved → sent` (or `→ failed`)
- `mentions.status`: `new → drafted → approved → replied` (or `→ skipped/spam`)
- `replies.status`: `pending → approved → sent`

---

## Setup checklist (do once)

1. Run `db/schema.sql` in Supabase SQL Editor.
2. Drop into `.env.local`:
   - `ANTHROPIC_API_KEY`
   - `SUPABASE_SERVICE_KEY` (service-role, secret)
   - `X_API_KEY`, `X_API_SECRET`, `X_BEARER_TOKEN`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`
3. `npm run dev` (dashboard on :3000)
4. `npm run worker:dev` (in another terminal)
5. Hit `POST /api/audience/refresh` to populate the audience table.

---

## Build Order (6 hours, 4 people)

| Hour | P1 (Platform) | P2 (X integration) | P3 (AI/Drafting) | P4 (UI/Dashboard) |
|------|---------------|--------------------|------------------|-------------------|
| 1 | ✅ Schema (incl. audience), env, supabase clients, types | ✅ `lib/x-client.ts` (post, reply, mentions, followers) | ✅ Anthropic client + prompts | Gut placeholder, dashboard route |
| 2 | ✅ Worker harness + cron | ✅ post-scheduled, fire-replies, poll-mentions in worker | ✅ `/api/draft`, `/api/reply` | `/draft` page UI |
| 3 | Twilio SMS skeleton | (polish error handling) | ✅ `/api/audience/refresh` (follower segmentation) | `/approve` page |
| 4 | SMS round-trip | (rate limit handling) | (audience-aware drafts) | `/inbox` page |
| 5 | (integration testing) | (polish) | (polish) | `/stats`, `/audience`, `/settings` |
| 6 | README, deploy, demo script | (polish) | (polish) | Landing polish |

---

## Connection to Ara (storytelling, not technical)

Ara markets: persistent personal AI computer, phone access, browser auto,
24/7 sandbox. We mirror those capabilities for the social-media use case
without depending on Ara's API:

| Ara capability | Our analog |
|---|---|
| Persistent sandbox | Worker process + Supabase persistent state |
| Phone access | Twilio SMS approval flow |
| Tool integrations | `lib/x-client.ts` + Anthropic + Supabase |
| Always-on automation | Worker runs on a VM / Railway / Fly |
| `@ara.tool` primitive | Discrete worker jobs (`firePosts`, `fireReplies`, `pollMentions`) |
| Audience awareness | Follower segmentation pipeline (X API → Anthropic) |

Pitch framing: *"We took the capabilities Ara shows off in their docs and built
a focused, self-contained version for one job: managing your X presence."*

---

## Demo Flow (target ≤ 5 minutes)

1. Open dashboard. Empty queue.
2. `/draft` → type *"thoughts on vibe coding"* → 3 variants stream in (Anthropic) → pick → schedule for +60s.
3. Show row in Supabase live (queue table updates).
4. Phone buzzes — SMS: *"Posting in 30s: '...'. Reply Y to confirm or N to cancel."*
5. Reply Y. Worker picks up flag, X API (twitter-api-v2) drives Chrome, tweet appears live on X.
6. Open `/inbox`. New mention. AI-drafted reply already there. Edit one word, click ✓.
7. Worker fires reply via X API (twitter-api-v2). Live on X.

Two channels (web + SMS), end-to-end, in under 5 minutes.

---

## .env.local (Next.js)

```
ANTHROPIC_API_KEY=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=                 # server only

# Optional Twilio (SMS approval)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
USER_PHONE_NUMBER=
```

---

## Non-Goals (cut to ship)

- Bluesky / LinkedIn / Threads / Instagram
- Image/video posting
- Multi-account
- Analytics beyond likes/replies/views as scraped
- Self-hosted worker (deploy to Railway/Fly free tier instead)
