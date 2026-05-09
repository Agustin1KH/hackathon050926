"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import type { ScheduledRow, ScheduledStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Check, Loader2, X } from "lucide-react";

export function ApproveList({ rows }: { rows: ScheduledRow[] }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [busyId, setBusyId] = useState<string | null>(null);

  async function update(id: string, status: ScheduledStatus | "deleted") {
    setBusyId(id);
    try {
      if (status === "deleted") {
        // Reject = delete row.
        await fetch("/api/schedule", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id, status: "failed" }),
        });
      } else {
        await fetch("/api/schedule", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id, status }),
        });
      }
      startTransition(() => router.refresh());
    } finally {
      setBusyId(null);
    }
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Queue is empty. Generate a draft to get started.
      </div>
    );
  }

  return (
    <div className="grid gap-3">
      {rows.map((r) => {
        const dt = new Date(r.scheduled_for);
        const due = dt.getTime() <= Date.now();
        return (
          <Card key={r.id}>
            <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex flex-col gap-2">
                <p className="text-sm leading-snug">{r.content}</p>
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <Badge
                    variant="outline"
                    className={
                      r.status === "approved"
                        ? "border-emerald-500/40 text-emerald-500"
                        : "border-yellow-500/40 text-yellow-500"
                    }
                  >
                    {r.status}
                  </Badge>
                  <span className="tabular-nums">
                    {due && r.status === "approved"
                      ? "firing imminently"
                      : `scheduled ${dt.toLocaleString()}`}
                  </span>
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                {r.status === "pending" ? (
                  <Button
                    size="sm"
                    onClick={() => update(r.id, "approved")}
                    disabled={busyId === r.id || pending}
                    data-icon="inline-end"
                  >
                    {busyId === r.id ? (
                      <Loader2 className="animate-spin" />
                    ) : (
                      <>
                        Approve
                        <Check />
                      </>
                    )}
                  </Button>
                ) : null}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => update(r.id, "deleted")}
                  disabled={busyId === r.id || pending}
                  data-icon="inline-end"
                >
                  Reject
                  <X />
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
