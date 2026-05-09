# Atlas — your X social agent

An AI agent that drafts, schedules, and replies to your X (Twitter) presence —
**tuned to who actually follows you**.

- **Draft posts in your voice.** Anthropic generates 3 variants per topic,
  shaped by your follower segmentation (devs, founders, marketers, …).
- **Schedule + approve.** Pending drafts wait in the queue. Approve via the
  dashboard (or by SMS, if you wire up Twilio). The worker fires them via the
  X API at the scheduled time.
- **Inbox triage.** Worker polls mentions every 5 minutes; AI drafts a reply
  for each. Approve, edit, or skip.
- **Audience analysis.** Pulls your followers via X API, classifies bios into
  segments, surfaces the breakdown.

Built for the Ara hackathon. Standalone — does not depend on Ara at runtime.
Inspired by Ara's capability set (persistent agent, phone access, browser
automation, always-on) for one focused job: managing your X presence.

---

## Stack

- **Next.js 16** (App Router, Turbopack), React 19, TypeScript, Tailwind v4 + shadcn
- **Supabase** Postgres for state (drafts, scheduled, sent_log, mentions, replies, audience, config)
- **Anthropic SDK** (`claude-sonnet-4-6`) for drafting / classification / segmentation
- **`twitter-api-v2`** for posting, mentions, and follower analysis
- **Node + `node-cron`** worker for scheduled posting + inbox polling
- **Twilio (optional)** for SMS approval flow

---

## Setup

### 1. Provision Supabase
1. Create a project at [supabase.com](https://supabase.com).
2. SQL Editor → paste `db/schema.sql` → Run.
3. (Hackathon-friendly) Disable RLS on the new tables:
   ```sql
   alter table drafts disable row level security;
   alter table scheduled disable row level security;
   alter table sent_log disable row level security;
   alter table mentions disable row level security;
   alter table replies disable row level security;
   alter table audience disable row level security;
   alter table config disable row level security;
   ```

### 2. Create the X / Twitter app
1. [developer.x.com](https://developer.x.com) → Project + App on Free tier.
2. App → User authentication settings → **Read and write** → save.
3. Keys and Tokens → generate (or copy):
   - API Key, API Key Secret
   - Bearer Token
   - Access Token, Access Token Secret

### 3. Get an Anthropic API key
[console.anthropic.com](https://console.anthropic.com) → API Keys.

### 4. Drop everything in `.env.local`

```bash
NEXT_PUBLIC_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...   # service-role, server only

ANTHROPIC_API_KEY=sk-ant-...

X_API_KEY=
X_API_SECRET=
X_BEARER_TOKEN=
X_ACCESS_TOKEN=
X_ACCESS_SECRET=

# Optional: SMS approval via Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
USER_PHONE_NUMBER=
```

### 5. Run

```bash
npm install
npm run dev          # dashboard at http://localhost:3000
npm run worker:dev   # in another terminal — fires posts + polls mentions
```

Then in the dashboard:
1. **Settings** → set your voice profile + post schedule.
2. **Audience** → click *Refresh* to pull and classify your followers.
3. **Draft** → type a topic → pick a variant → schedule it.
4. **Approve** → click Approve. The worker will post on schedule.

---

## Repo map

```
app/
  page.tsx               # dashboard
  draft/                 # generate variants → queue
  approve/               # pending posts review
  inbox/                 # mentions + AI replies
  audience/              # follower segmentation
  settings/              # voice + schedule
  api/
    draft/               # POST topic → variants
    reply/               # POST mentionId → drafted reply, PATCH approve
    schedule/            # GET/POST/PATCH scheduled queue
    audience/refresh/    # POST → fetch + classify followers
    settings/            # POST upsert config

worker/
  index.ts               # cron: fire posts every minute, poll mentions every 5

lib/
  supabase.ts            # browser client (anon)
  supabase-server.ts     # server client (service-role)
  x-client.ts            # twitter-api-v2 wrapper
  anthropic.ts           # SDK client
  prompts.ts             # voice / draft / classify / segment templates
  types.ts               # mirrors db/schema.sql

db/
  schema.sql             # one file, run once in Supabase
```

---

## Demo script (≤ 5 min)

1. Open `localhost:3000` → empty dashboard, 0 across the board.
2. **Audience → Refresh**. Wait ~30s. Card shows "60% developers, 25% founders…".
3. **Draft** → "thoughts on vibe coding" → 3 variants stream in, all tuned to that audience.
4. Pick variant, schedule for `+60s`. Click *Add to queue*.
5. **Approve** → click *Approve* on the pending row.
6. Show Supabase live → row goes `approved` → `sent` within a minute.
7. Check x.com → tweet is live.
8. **Inbox** → click *Draft reply* on a mention → AI draft appears → *Approve & send* → reply lives on X.

Total: under 5 minutes, end-to-end, two channels (drafting + replying), with
audience-aware tuning as the standout feature.

---

## Connection to Ara (storytelling)

| Ara capability | Atlas analog |
|---|---|
| Persistent sandbox | Worker process + Supabase persistent state |
| Phone access | Optional Twilio SMS approval flow |
| Tool integrations | `lib/x-client.ts` + Anthropic + Supabase |
| Always-on automation | Worker deployable to Railway / Fly free tier |
| `@ara.tool` primitives | Discrete worker jobs (`firePosts`, `fireReplies`, `pollMentions`) |
| (New) Audience awareness | Follower segmentation pipeline (X API → Anthropic) |

We took the capabilities Ara markets and built a focused, self-contained
version for one job: **managing your X presence in a way that's actually tuned
to who follows you.**
