"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Loader2, RotateCw } from "lucide-react";

export function AudienceRefresh() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [pending, startTransition] = useTransition();
  const [err, setErr] = useState<string | null>(null);

  async function refresh() {
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch("/api/audience/refresh", { method: "POST" });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error ?? `${res.status}`);
      }
      startTransition(() => router.refresh());
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button onClick={refresh} disabled={busy || pending} data-icon="inline-end">
        {busy ? (
          <>
            Refreshing
            <Loader2 className="animate-spin" />
          </>
        ) : (
          <>
            Refresh
            <RotateCw />
          </>
        )}
      </Button>
      {err && (
        <p className="text-[11px] text-destructive">{err}</p>
      )}
    </div>
  );
}
