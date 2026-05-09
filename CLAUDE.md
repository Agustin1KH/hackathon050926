# Social Media Agent — Hackathon Build Plan

## Concept
A standalone social media agent that manages your X (Twitter) presence —
drafting posts, scheduling them, and triaging mentions/DMs with AI-drafted
replies. Approve from a **web dashboard** or by **replying Y/N to a text**.
Posting uses **browser automation** (Playwright), not the X API, so there's
no developer review, no token rotation, and no per-month tweet caps.

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
│ Worker (Node + Playwright)          │
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

## Why browser automation instead of X API

| Concern | X API | Playwright (this approach) |
|---|---|---|
| Dev approval | Required, can take days | None |
| Free-tier post cap | 500/month | Unlimited (your account's normal limits) |
| OAuth complexity | OAuth 2.0 PKCE flow | One-time login in headed Chrome, session persists |
| DM access | Basic tier ($100/mo) | Free, just navigate to DM page |
| Maintenance | Token refresh, rate limits | Selectors break occasionally; mitigate with stable test IDs |

Tradeoffs accepted: Playwright is more fragile (X can change DOM), but for a
hackathon the friction-free auth + unlimited posting wins. Selectors live in
one file (`worker/x-selectors.ts`) so updates are localized.

---

## Stack

| Layer | Tool | Why |
|---|---|---|
| Dashboard | **Next.js 16** + AI SDK 6 + shadcn (existing scaffold) | Already wired |
| AI | **Anthropic SDK** (`@anthropic-ai/sdk`), model `claude-sonnet-4-6` | Direct API; AI Gateway also OK |
| State | **Supabase** (Postgres) | REST API + auth + free tier; provisioned |
| Browser | **Playwright** (Node) | Drives real Chrome with persistent session |
| Worker | **Node** + `node-cron` | Same runtime as Next.js, easy deploy |
| SMS (optional) | **Twilio** | Inbound webhook → Supabase flag flip |

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
│   ├── index.ts               # cron loop, registers jobs
│   ├── browser.ts             # Playwright session manager
│   ├── x-selectors.ts         # X DOM selectors (single source)
│   ├── jobs/
│   │   ├── post-scheduled.ts  # fire approved scheduled posts
│   │   ├── post-replies.ts    # fire approved replies
│   │   └── poll-mentions.ts   # scrape /notifications/mentions
│   └── login.ts               # one-time headed login flow
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

## Login flow (one-time, headed)

```bash
npm run worker:login
```
Opens a real Chrome window. User logs into x.com normally. Playwright saves
the auth state to `worker/.auth/x.json` (gitignored). All subsequent posting
uses that saved session — no credentials in env vars.

---

## Build Order (6 hours, 4 people)

| Hour | P1 (Platform) | P2 (Browser/Posting) | P3 (AI/Drafting) | P4 (UI/Dashboard) |
|------|---------------|----------------------|------------------|-------------------|
| 1 | ✅ Schema, env, supabase clients, types | Playwright install + login flow | Anthropic SDK setup, draft prompt working | Gut placeholder, dashboard route |
| 2 | Worker harness + cron registry | `post_tweet` via Playwright works end-to-end | `/api/draft` returns 3 variants | `/draft` page UI |
| 3 | Twilio SMS skeleton | `get_mentions` scraping works | `/api/classify`, `/api/reply` | `/approve` page |
| 4 | SMS round-trip | `reply_to` works | (polish prompts) | `/inbox` page |
| 5 | (integration testing) | (polish, error handling) | (polish) | `/stats`, `/settings` |
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
| Browser tools | Playwright with saved session |
| Always-on automation | Worker runs on a VM / Railway / Fly |
| `@ara.tool` primitive | Discrete worker jobs (`post`, `reply`, `mentions`) |

Pitch framing: *"We took the capabilities Ara shows off in their docs and built
a focused, self-contained version for one job: managing your X presence."*

---

## Demo Flow (target ≤ 5 minutes)

1. Open dashboard. Empty queue.
2. `/draft` → type *"thoughts on vibe coding"* → 3 variants stream in (Anthropic) → pick → schedule for +60s.
3. Show row in Supabase live (queue table updates).
4. Phone buzzes — SMS: *"Posting in 30s: '...'. Reply Y to confirm or N to cancel."*
5. Reply Y. Worker picks up flag, Playwright drives Chrome, tweet appears live on X.
6. Open `/inbox`. New mention. AI-drafted reply already there. Edit one word, click ✓.
7. Worker fires reply via Playwright. Live on X.

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
