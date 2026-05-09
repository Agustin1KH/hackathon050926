import { supabaseAdmin } from "@/lib/supabase-server";
import { AudienceRefresh } from "./audience-refresh";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AudienceRow, AudienceSegment } from "@/lib/types";

export const dynamic = "force-dynamic";
export const metadata = { title: "Audience" };

export default async function AudiencePage() {
  const { data } = await supabaseAdmin
    .from("audience")
    .select("*")
    .order("follower_cnt", { ascending: false });
  const rows = (data ?? []) as AudienceRow[];

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
  for (const r of rows) if (r.segment) segments[r.segment]++;
  const total = rows.length;

  return (
    <>
      <header className="flex items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="font-heading text-3xl font-semibold tracking-tight">
            Audience
          </h1>
          <p className="text-sm text-muted-foreground">
            Follower segmentation. Atlas reads each follower&apos;s bio, classifies
            it, and uses the breakdown to tune every draft.
          </p>
        </div>
        <AudienceRefresh />
      </header>

      {total === 0 ? (
        <div className="rounded-md border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          No followers fetched yet. Click <span className="font-mono">Refresh</span> to pull from the X API.
        </div>
      ) : (
        <>
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(segments)
              .sort((a, b) => b[1] - a[1])
              .filter(([, n]) => n > 0)
              .map(([seg, n]) => {
                const pct = total ? Math.round((n / total) * 100) : 0;
                return (
                  <Card key={seg}>
                    <CardContent className="flex flex-col gap-1 p-4">
                      <span className="text-xs text-muted-foreground capitalize">
                        {seg}
                      </span>
                      <span className="font-heading text-2xl font-semibold tabular-nums">
                        {pct}%
                      </span>
                      <span className="text-[11px] text-muted-foreground tabular-nums">
                        {n} of {total}
                      </span>
                    </CardContent>
                  </Card>
                );
              })}
          </section>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Top followers</CardTitle>
              <CardDescription>
                Ranked by follower count. Useful for spotting key amplifiers.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {rows.slice(0, 25).map((r) => (
                <div
                  key={r.id}
                  className="flex items-center justify-between gap-3 rounded-md border border-border bg-card/40 p-2"
                >
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-medium">{r.name ?? r.username}</span>
                      <span className="font-mono text-[11px] text-muted-foreground">
                        @{r.username}
                      </span>
                    </div>
                    <p className="line-clamp-1 text-xs text-muted-foreground">
                      {r.bio || "(no bio)"}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {r.segment && (
                      <Badge
                        variant="outline"
                        className="capitalize px-1.5 py-0 text-[10px]"
                      >
                        {r.segment}
                      </Badge>
                    )}
                    <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                      {(r.follower_cnt ?? 0).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </>
  );
}
