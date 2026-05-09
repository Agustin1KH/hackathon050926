import { supabaseAdmin } from "@/lib/supabase-server";
import { ApproveList } from "./approve-list";
import type { ScheduledRow } from "@/lib/types";

export const dynamic = "force-dynamic";
export const metadata = { title: "Approve" };

export default async function ApprovePage() {
  const { data } = await supabaseAdmin
    .from("scheduled")
    .select("*")
    .in("status", ["pending", "approved"])
    .order("scheduled_for", { ascending: true });

  return (
    <>
      <header className="flex flex-col gap-1">
        <h1 className="font-heading text-3xl font-semibold tracking-tight">
          Approve
        </h1>
        <p className="text-sm text-muted-foreground">
          Pending drafts wait here. Approve and the worker fires them at their
          scheduled time. Reject removes them from the queue.
        </p>
      </header>
      <ApproveList rows={(data ?? []) as ScheduledRow[]} />
    </>
  );
}
