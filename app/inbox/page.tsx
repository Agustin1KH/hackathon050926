import { supabaseAdmin } from "@/lib/supabase-server";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { MentionRow, ReplyRow } from "@/lib/types";
import { InboxControls } from "./inbox-controls";

export const dynamic = "force-dynamic";
export const metadata = { title: "Inbox" };

export default async function InboxPage() {
  const { data: mentions } = await supabaseAdmin
    .from("mentions")
    .select("*")
    .in("status", ["new", "drafted", "approved"])
    .order("fetched_at", { ascending: false })
    .limit(40);
  const { data: replies } = await supabaseAdmin.from("replies").select("*");

  const repliesByMention = new Map<string, ReplyRow>();
  for (const r of (replies ?? []) as ReplyRow[]) {
    if (r.mention_id) repliesByMention.set(r.mention_id, r);
  }

  const rows = ((mentions ?? []) as MentionRow[]).map((m) => ({
    mention: m,
    reply: repliesByMention.get(m.id) ?? null,
  }));

  return (
    <>
      <header className="flex flex-col gap-1">
        <h1 className="font-heading text-3xl font-semibold tracking-tight">
          Inbox
        </h1>
        <p className="text-sm text-muted-foreground">
          The worker polls X mentions every 5 min. Atlas drafts replies for each
          one — approve and the worker fires it.
        </p>
      </header>

      {rows.length === 0 ? (
        <div className="rounded-md border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          No new mentions. Worker will populate this on the next poll.
        </div>
      ) : (
        <div className="grid gap-3">
          {rows.map(({ mention, reply }) => (
            <Card key={mention.id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">
                  @{mention.author ?? "unknown"}
                </CardTitle>
                <CardDescription className="text-xs">
                  {new Date(mention.fetched_at).toLocaleString()} · status:{" "}
                  <span className="capitalize">{mention.status}</span>
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="rounded-md border border-border bg-card/40 p-3 text-sm">
                  {mention.text}
                </div>
                <InboxControls mention={mention} reply={reply} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
