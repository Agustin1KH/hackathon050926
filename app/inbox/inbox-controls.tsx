"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import type { MentionRow, ReplyRow } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Sparkles, Check, X } from "lucide-react";

export function InboxControls({
  mention,
  reply,
}: {
  mention: MentionRow;
  reply: ReplyRow | null;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [content, setContent] = useState(reply?.draft_content ?? "");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function generate() {
    setBusy("generate");
    setErr(null);
    try {
      const res = await fetch("/api/reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mentionId: mention.id }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? "failed");
      setContent(json.drafts?.[0] ?? "");
      startTransition(() => router.refresh());
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  async function approve() {
    if (!reply) return;
    setBusy("approve");
    try {
      // PATCH replies via /api/reply/[id]? Inline call to Supabase via
      // /api/schedule pattern would be cleaner; for hackathon we hit a small
      // approval endpoint.
      const res = await fetch("/api/reply", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: reply.id, status: "approved", content }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error ?? "approve failed");
      }
      startTransition(() => router.refresh());
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  async function skip() {
    setBusy("skip");
    try {
      const res = await fetch("/api/reply", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mentionId: mention.id, mentionStatus: "skipped" }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.error ?? "skip failed");
      }
      startTransition(() => router.refresh());
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {!reply ? (
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">No reply drafted yet.</span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={skip}
              disabled={busy === "skip" || pending}
              data-icon="inline-end"
            >
              Skip
              <X />
            </Button>
            <Button
              size="sm"
              onClick={generate}
              disabled={busy === "generate" || pending}
              data-icon="inline-end"
            >
              {busy === "generate" ? (
                <Loader2 className="animate-spin" />
              ) : (
                <>
                  Draft reply
                  <Sparkles />
                </>
              )}
            </Button>
          </div>
        </div>
      ) : (
        <>
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={3}
            maxLength={280}
            className="font-mono text-sm"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground tabular-nums">
              {content.length}/280
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={skip}
                disabled={!!busy || pending}
                data-icon="inline-end"
              >
                Skip
                <X />
              </Button>
              <Button
                size="sm"
                onClick={generate}
                disabled={!!busy || pending}
                variant="ghost"
                data-icon="inline-end"
              >
                Redraft
                <Sparkles />
              </Button>
              <Button
                size="sm"
                onClick={approve}
                disabled={!!busy || pending || content.length === 0}
                data-icon="inline-end"
              >
                {busy === "approve" ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <>
                    Approve & send
                    <Check />
                  </>
                )}
              </Button>
            </div>
          </div>
        </>
      )}
      {err && (
        <p className="rounded-md border border-destructive/40 bg-destructive/10 p-2 text-xs text-destructive">
          {err}
        </p>
      )}
    </div>
  );
}
