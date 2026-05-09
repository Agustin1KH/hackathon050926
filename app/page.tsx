import {
  ArrowUpRight,
  Boxes,
  Brain,
  Code2,
  Database,
  Gamepad2,
  Globe,
  Layers,
  Layout,
  LineChart,
  Rocket,
  Sparkles,
  Wand2,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { LaunchChat } from "@/components/launch-chat";

const STACK = [
  { label: "Next.js 16", desc: "App Router · Turbopack" },
  { label: "React 19", desc: "Server Components" },
  { label: "TypeScript 5", desc: "strict mode" },
  { label: "Tailwind v4", desc: "shadcn theme" },
  { label: "shadcn/ui", desc: "radix primitives" },
  { label: "AI SDK 6", desc: "Vercel AI Gateway" },
  { label: "Vercel", desc: "one-click deploy" },
];

const PIVOTS: Array<{
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  prompt: string;
}> = [
  {
    icon: Brain,
    title: "AI tool / agent",
    description:
      "A focused assistant that takes one input and produces one delightful output (summarize, rewrite, plan, classify…).",
    prompt:
      "Pitch 5 single-purpose AI tools I can ship in 24h with Next.js + AI SDK + Vercel.",
  },
  {
    icon: Layout,
    title: "Internal tool / dashboard",
    description:
      "Visualize a dataset or workflow. Strong design + a few good filters wins demo day.",
    prompt:
      "Design a 1-page dashboard for a hackathon-friendly dataset (sports, weather, GitHub, transit). Pick the data and sketch the UI.",
  },
  {
    icon: Globe,
    title: "Consumer mini-app",
    description:
      "A tiny site that does one fun thing. Shareable, opinionated, and easy to demo on a phone.",
    prompt:
      "Brainstorm 5 consumer mini-apps that are funny, shareable, and buildable in a weekend.",
  },
  {
    icon: Gamepad2,
    title: "Multiplayer / live",
    description:
      "Real-time, low-latency. Voting, draw-together, room-based games.",
    prompt:
      "Compare options for adding real-time multiplayer to a Next.js app at a hackathon (websockets, partykit, supabase realtime, ably). Pick one.",
  },
  {
    icon: Database,
    title: "Data + RAG",
    description:
      "Grab a public dataset, embed it, build a chat over it. Good for technical depth.",
    prompt:
      "Walk me through building RAG over a CSV in a Next.js app using AI SDK embeddings and a simple vector store.",
  },
  {
    icon: LineChart,
    title: "Devtool",
    description:
      "Build something the judges (engineers) actually want to use.",
    prompt:
      "Suggest 5 small developer tools I could build this weekend that engineers would star on GitHub.",
  },
];

export default function HomePage() {
  return (
    <div className="relative isolate">
      <BackgroundDecoration />

      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 pt-6">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-foreground text-background">
            <Sparkles className="h-3.5 w-3.5" />
          </div>
          <span className="font-mono text-sm tracking-tight">
            hackathon
            <span className="text-muted-foreground">050926</span>
          </span>
        </div>
        <nav className="flex items-center gap-1">
          <Button variant="ghost" size="sm" asChild>
            <a href="https://nextjs.org/docs" target="_blank" rel="noreferrer">
              Docs
            </a>
          </Button>
          <Button variant="ghost" size="sm" asChild>
            <a
              href="https://ai-sdk.dev/docs"
              target="_blank"
              rel="noreferrer"
            >
              AI SDK
            </a>
          </Button>
          <Button size="sm" asChild>
            <a
              href="https://vercel.com/new"
              target="_blank"
              rel="noreferrer"
              data-icon="inline-end"
            >
              Deploy
              <ArrowUpRight />
            </a>
          </Button>
        </nav>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-col gap-16 px-6 pt-14 pb-24">
        <HeroSection />
        <StackSection />
        <BuildSection />
        <QuickStartSection />
      </main>

      <footer className="border-t bg-background/80">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-start justify-between gap-3 px-6 py-6 text-xs text-muted-foreground sm:flex-row sm:items-center">
          <div className="font-mono">
            hackathon050926 · launchpad ·{" "}
            <span className="text-foreground/70">
              {new Date().getUTCFullYear()}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com/vercel/next.js"
              className="inline-flex items-center gap-1 hover:text-foreground"
              target="_blank"
              rel="noreferrer"
            >
              <Code2 className="h-3.5 w-3.5" />
              source
            </a>
            <a
              href="https://vercel.com"
              className="inline-flex items-center gap-1 hover:text-foreground"
              target="_blank"
              rel="noreferrer"
            >
              <Rocket className="h-3.5 w-3.5" />
              vercel
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function HeroSection() {
  return (
    <section className="flex flex-col gap-6">
      <Badge variant="outline" className="self-start gap-1.5 px-2 py-0.5 text-[11px]">
        <span
          className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_theme(colors.emerald.500)]"
          aria-hidden
        />
        Repo initialized · ready to build
      </Badge>

      <h1 className="text-balance font-heading text-4xl leading-[1.05] font-semibold tracking-tight sm:text-5xl md:text-6xl">
        Your hackathon{" "}
        <span className="bg-gradient-to-br from-foreground via-foreground to-foreground/40 bg-clip-text text-transparent">
          launchpad.
        </span>
      </h1>
      <p className="max-w-2xl text-pretty text-base text-muted-foreground sm:text-lg">
        A Next.js 16 + AI SDK starter pre-wired so you can decide on the idea
        later — and ship before sunrise. Open the chat below to brainstorm,
        scaffold, and pivot.
      </p>

      <div className="flex flex-wrap items-center gap-2 pt-1">
        <Button asChild>
          <a href="#build" data-icon="inline-end">
            Pick a direction
            <Zap />
          </a>
        </Button>
        <Button variant="outline" asChild>
          <a href="#quickstart">Quick start</a>
        </Button>
        <span className="ml-1 font-mono text-xs text-muted-foreground">
          $ npm run dev
        </span>
      </div>
    </section>
  );
}

function StackSection() {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-medium">
            <Layers className="h-4 w-4 text-muted-foreground" />
            Pre-wired stack
          </h2>
          <p className="text-xs text-muted-foreground">
            Battle-tested defaults. Throw out anything you don&apos;t need.
          </p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-7">
        {STACK.map((s) => (
          <div
            key={s.label}
            className="rounded-lg border border-border bg-card/60 px-3 py-2.5 text-xs ring-1 ring-foreground/5"
          >
            <div className="font-medium">{s.label}</div>
            <div className="font-mono text-[10px] text-muted-foreground">
              {s.desc}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function BuildSection() {
  return (
    <section id="build" className="grid gap-8 lg:grid-cols-[1.1fr_1fr]">
      <div className="flex flex-col gap-4">
        <div>
          <h2 className="font-heading text-2xl font-semibold tracking-tight">
            Pick a direction.
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Six lenses for the same blank repo. Tap any card to ask the assistant
            to dive deeper — the prompt is wired up.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {PIVOTS.map((pivot) => (
            <PivotCard key={pivot.title} {...pivot} />
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <div>
          <h2 className="font-heading text-2xl font-semibold tracking-tight">
            Or just start typing.
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The chat below talks to the Vercel AI Gateway via the AI SDK — your
            repo&apos;s first working feature.
          </p>
        </div>
        <LaunchChat />
      </div>
    </section>
  );
}

function PivotCard({
  icon: Icon,
  title,
  description,
  prompt,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  prompt: string;
}) {
  return (
    <Card className="group/card transition-colors hover:bg-accent/40">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-muted text-muted-foreground ring-1 ring-border group-hover/card:bg-foreground group-hover/card:text-background group-hover/card:ring-foreground">
            <Icon className="h-3.5 w-3.5" />
          </div>
          <CardTitle className="text-sm">{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <CardDescription className="text-xs leading-relaxed">
          {description}
        </CardDescription>
        <div className="rounded-md border border-dashed border-border bg-background/40 px-2.5 py-1.5 font-mono text-[11px] text-muted-foreground">
          &gt; {prompt}
        </div>
      </CardContent>
    </Card>
  );
}

function QuickStartSection() {
  return (
    <section id="quickstart" className="flex flex-col gap-4">
      <div>
        <h2 className="font-heading text-2xl font-semibold tracking-tight">
          Quick start.
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Three commands, one env var, and you&apos;re live.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <StepCard
          step="1"
          icon={Boxes}
          title="Install"
          body={`npm install`}
          hint="Already done if you ran create-next-app."
        />
        <StepCard
          step="2"
          icon={Wand2}
          title="Configure AI"
          body={`# .env.local\nAI_GATEWAY_API_KEY=\nAI_MODEL=openai/gpt-5.4-mini`}
          hint="Get a key at vercel.com/ai-gateway. Skip if you don't need AI."
        />
        <StepCard
          step="3"
          icon={Rocket}
          title="Run"
          body={`npm run dev`}
          hint="Open http://localhost:3000 and start hacking."
        />
      </div>

      <Separator className="my-2" />

      <div className="flex flex-col gap-1 text-xs text-muted-foreground">
        <div className="font-mono text-foreground/80">repo map</div>
        <pre className="overflow-x-auto rounded-lg border border-border bg-card/60 p-3 font-mono text-[11px] leading-relaxed">{`app/
  layout.tsx          # root html, fonts, dark mode
  page.tsx            # this landing page (delete or rewrite)
  api/
    chat/route.ts     # AI SDK streamText route handler
  globals.css         # tailwind v4 + shadcn theme
components/
  launch-chat.tsx     # client chat using @ai-sdk/react
  ui/                 # shadcn primitives
lib/
  utils.ts            # cn() helper`}</pre>
      </div>
    </section>
  );
}

function StepCard({
  step,
  icon: Icon,
  title,
  body,
  hint,
}: {
  step: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  body: string;
  hint: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-muted font-mono text-[10px] text-muted-foreground ring-1 ring-border">
            {step}
          </div>
          <CardTitle className="flex items-center gap-1.5 text-sm">
            <Icon className="h-3.5 w-3.5 text-muted-foreground" />
            {title}
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <pre className="overflow-x-auto rounded-md border border-border bg-background/60 px-2.5 py-2 font-mono text-[11px] leading-relaxed">
          {body}
        </pre>
        <p className="text-[11px] text-muted-foreground">{hint}</p>
      </CardContent>
    </Card>
  );
}

function BackgroundDecoration() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(circle at 50% -10%, color-mix(in oklab, var(--foreground) 9%, transparent), transparent 55%)",
        }}
      />
      <div
        className="absolute inset-0 opacity-[0.16]"
        style={{
          backgroundImage:
            "radial-gradient(color-mix(in oklab, var(--foreground) 60%, transparent) 1px, transparent 1px)",
          backgroundSize: "22px 22px",
          maskImage:
            "linear-gradient(to bottom, black, transparent 85%)",
          WebkitMaskImage:
            "linear-gradient(to bottom, black, transparent 85%)",
        }}
      />
    </div>
  );
}
