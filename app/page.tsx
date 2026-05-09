import Link from "next/link";
import { supabaseAdmin } from "@/lib/supabase-server";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Calendar,
  CheckCircle2,
  Clock,
  Inbox,
  Send,
  Users,
} from "lucide-react";
import { audienceSummary } from "@/lib/prompts";
import type { AudienceSegment, SentLogRow } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  // Pull all stat counters in parallel.
  const [pending, approved, mentionsNew, audienceRows, recentSent] =
    await Promise.all([
      supabaseAdmin
        .from("scheduled")
        .select("*", { count: "exact", head: true })
        .eq("status", "pending"),
      supabaseAdmin
        .from("scheduled")
        .select("*", { count: "exact", head: true })
        .eq("status", "approved"),
      supabaseAdmin
        .from("mentions")
        .select("*", { count: "exact", head: true })
        .eq("status", "new"),
      supabaseAdmin.from("audience").select("segment"),
      supabaseAdmin
        .from("sent_log")
        .select("*")
        .order("sent_at", { ascending: false })
        .limit(5),
    ]);

  const segments: Record<AudienceSegment, number> = {
    developers: 0,
    founders: 0,
    marketers: 0,
    designers: 0,
    investors: 0,
    creators: 0,
    students: 0,
    other: 0,
  };
  for (const row of audienceRows.data ?? []) {
    const s = (row as { segment: AudienceSegment | null }).segment;
    if (s && s in segments) segments[s] += 1;
  }
  const audienceTotal = Object.values(segments).reduce((a, b) => a + b, 0);

  return (
    <>
      <header className="flex items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="font-heading text-3xl font-semibold tracking-tight">
            Dashboard
          </h1>
          <p className="text-sm text-muted-foreground">
            Atlas drafts, schedules, and triages your X presence — tuned to who
            actually follows you.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href="/audience">Refresh audience</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/draft">New draft</Link>
          </Button>
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Clock}
          label="Pending review"
          value={pending.count ?? 0}
          hint="Drafts waiting for approval"
          href="/approve"
        />
        <StatCard
          icon={Calendar}
          label="Approved & queued"
          value={approved.count ?? 0}
          hint="Will fire on schedule"
          href="/approve"
        />
        <StatCard
          icon={Inbox}
          label="New mentions"
          value={mentionsNew.count ?? 0}
          hint="Awaiting AI triage"
          href="/inbox"
        />
        <StatCard
          icon={Users}
          label="Audience"
          value={audienceTotal}
          hint={
            audienceTotal === 0
              ? "Click ‘Refresh audience’ to populate"
              : audienceSummary(segments)
          }
          href="/audience"
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Send className="h-4 w-4 text-muted-foreground" />
              Recent posts
            </CardTitle>
            <CardDescription>
              Last 5 tweets fired by the worker.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {(recentSent.data ?? []).length === 0 ? (
              <EmptyState>
                Nothing yet. Approve a draft and the worker will fire it on
                schedule.
              </EmptyState>
            ) : (
              (recentSent.data as SentLogRow[]).map((r) => (
                <div
                  key={r.id}
                  className="flex flex-col gap-1 rounded-md border border-border bg-card/40 p-3"
                >
                  <p className="text-sm leading-snug">{r.content}</p>
                  <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                    <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                    <span>
                      sent {new Date(r.sent_at).toLocaleString()}
                    </span>
                    {r.x_tweet_id && (
                      <Badge
                        variant="outline"
                        className="px-1.5 py-0 font-mono text-[10px]"
                      >
                        {r.x_tweet_id.slice(0, 8)}
                      </Badge>
                    )}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4 text-muted-foreground" />
              Audience snapshot
            </CardTitle>
            <CardDescription>
              Who actually reads you — used to tune every draft.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {audienceTotal === 0 ? (
              <EmptyState>
                No audience data yet. Visit{" "}
                <Link
                  href="/audience"
                  className="underline decoration-dotted underline-offset-2"
                >
                  Audience
                </Link>{" "}
                and click Refresh.
              </EmptyState>
            ) : (
              Object.entries(segments)
                .filter(([, n]) => n > 0)
                .sort((a, b) => b[1] - a[1])
                .map(([seg, n]) => {
                  const pct = Math.round((n / audienceTotal) * 100);
                  return <SegmentBar key={seg} label={seg} pct={pct} count={n} />;
                })
            )}
          </CardContent>
        </Card>
      </section>
    </>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  href,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  hint: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="group rounded-lg border border-border bg-card/60 p-4 transition-colors hover:bg-accent/40"
    >
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <Icon className="h-3.5 w-3.5" />
          {label}
        </span>
      </div>
      <div className="mt-2 font-heading text-3xl font-semibold tabular-nums">
        {value}
      </div>
      <div className="mt-1 line-clamp-1 text-[11px] text-muted-foreground">
        {hint}
      </div>
    </Link>
  );
}

function SegmentBar({
  label,
  pct,
  count,
}: {
  label: string;
  pct: number;
  count: number;
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs">
        <span className="capitalize">{label}</span>
        <span className="text-muted-foreground tabular-nums">
          {pct}% · {count}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-foreground/80"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground">
      {children}
    </div>
  );
}

