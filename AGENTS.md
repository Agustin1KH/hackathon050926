<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Project: hackathon050926 — launchpad

This repo is a Next.js 16 + AI SDK 6 hackathon scaffold. The team hasn't picked
the actual idea yet — `app/page.tsx` is a placeholder landing page meant to be
ripped out once a direction is chosen.

## Stack snapshot

- Next.js 16 (App Router, Turbopack), React 19, TypeScript 5
- Tailwind CSS v4 with shadcn/ui (`style: radix-nova`, base: neutral)
- AI SDK 6 (`ai`, `@ai-sdk/react`) routed via the **Vercel AI Gateway** (model
  IDs are plain strings like `openai/gpt-5.4-mini`)
- lucide-react v1 (note: brand icons like `Github` are no longer exported)

## Conventions

- Server components by default. Add `"use client"` only when needed.
- All Next.js dynamic APIs (`params`, `searchParams`, `cookies()`, `headers()`)
  are async — `await` them.
- Build UI from `components/ui/*` shadcn primitives, not raw HTML elements.
- Theme tokens (`bg-background`, `text-foreground`, `bg-card`, `border-border`,
  etc.) live in `app/globals.css`. Do not hardcode hex values.
- Dark mode is the default (`<html class="dark">` in `app/layout.tsx`). Both
  themes are wired.
- `convertToModelMessages` is **async** in AI SDK 6 — always `await` it.
- `useChat` uses `transport: new DefaultChatTransport({ api })` (not `{ api }`
  directly). Use `sendMessage({ text })`, not `handleSubmit`. Render
  `message.parts`, not `message.content`. Use `status === "streaming" || status === "submitted"`,
  not `isLoading`.

## Adding things

```bash
# shadcn components
npx shadcn@latest add table tabs select

# AI SDK provider extensions (rarely needed — Gateway handles it)
npm install @ai-sdk/openai
```

## Running

```bash
npm run dev        # http://localhost:3000
npm run build      # prod build
npx tsc --noEmit   # type check (faster than build for sanity checks)
```

## Files to know

- `app/page.tsx` — the placeholder landing page. Delete or rewrite once an
  idea is picked.
- `app/api/chat/route.ts` — the AI SDK chat handler. Edit the `SYSTEM_PROMPT`
  and `MODEL` here.
- `components/launch-chat.tsx` — the working client chat UI. Reference for any
  new chat surfaces.
- `app/globals.css` — Tailwind theme + shadcn tokens. Avoid editing the font
  literals (Tailwind v4 resolves them at parse time).
- `.env.local.example` — copy to `.env.local` for AI Gateway auth.
