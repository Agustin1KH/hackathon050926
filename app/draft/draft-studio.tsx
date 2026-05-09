"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Sparkles, Calendar } from "lucide-react";

function defaultScheduleIso() {
  const d = new Date();
  d.setMinutes(d.getMinutes() + 60);
  d.setSeconds(0, 0);
  // datetime-local needs YYYY-MM-DDTHH:mm without timezone
  return d.toISOString().slice(0, 16);
}

export function DraftStudio() {
  const [topic, setTopic] = useState("");
  const [variants, setVariants] = useState<string[]>([]);
  const [audience, setAudience] = useState<string>("");
  const [picked, setPicked] = useState<number | null>(null);
  const [editedContent, setEditedContent] = useState("");
  const [when, setWhen] = useState(defaultScheduleIso());
  const [loading, setLoading] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function generate() {
    setErr(null);
    setVariants([]);
    setPicked(null);
    setLoading(true);
    try {
      const res = await fetch("/api/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, n: 3 }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? "draft failed");
      setVariants(json.variants ?? []);
      setAudience(json.audience ?? "");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function schedule() {
    if (picked == null) return;
    setScheduling(true);
    setErr(null);
    setDone(null);
    try {
      const content = editedContent || variants[picked];
      const scheduled_for = new Date(when).toISOString();
      const res = await fetch("/api/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, scheduled_for }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? "schedule failed");
      setDone(`Queued for ${new Date(scheduled_for).toLocaleString()}.`);
      setTopic("");
      setVariants([]);
      setPicked(null);
      setEditedContent("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setScheduling(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">1. Topic</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Textarea
            placeholder="thoughts on vibe coding, or paste a URL, or describe the angle…"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            rows={5}
            className="font-mono text-sm"
          />
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-muted-foreground">
              {audience
                ? `Tuning for: ${audience}`
                : "Audience-aware once you’ve refreshed your follower data."}
            </p>
            <Button
              onClick={generate}
              disabled={!topic.trim() || loading}
              data-icon="inline-end"
            >
              {loading ? (
                <>
                  Drafting
                  <Loader2 className="animate-spin" />
                </>
              ) : (
                <>
                  Generate variants
                  <Sparkles />
                </>
              )}
            </Button>
          </div>
          {err && (
            <p className="rounded-md border border-destructive/40 bg-destructive/10 p-2 text-xs text-destructive">
              {err}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">2. Pick a variant</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {variants.length === 0 ? (
            <p className="rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground">
              Variants will appear here.
            </p>
          ) : (
            variants.map((v, i) => (
              <button
                key={i}
                onClick={() => {
                  setPicked(i);
                  setEditedContent(v);
                }}
                className={`flex flex-col gap-1.5 rounded-md border p-3 text-left transition-colors ${
                  picked === i
                    ? "border-foreground/60 bg-accent/40"
                    : "border-border hover:bg-accent/20"
                }`}
              >
                <Badge
                  variant="outline"
                  className="self-start px-1.5 py-0 text-[10px]"
                >
                  variant {i + 1}
                </Badge>
                <p className="text-sm leading-snug">{v}</p>
                <p className="text-[10px] text-muted-foreground tabular-nums">
                  {v.length} chars
                </p>
              </button>
            ))
          )}
        </CardContent>
      </Card>

      {picked !== null && (
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">3. Edit & schedule</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              rows={4}
              maxLength={280}
              className="font-mono text-sm"
            />
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-muted-foreground tabular-nums">
                {editedContent.length}/280
              </span>
              <div className="flex items-center gap-2">
                <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  type="datetime-local"
                  value={when}
                  onChange={(e) => setWhen(e.target.value)}
                  className="w-[14rem]"
                />
                <Button
                  onClick={schedule}
                  disabled={scheduling || editedContent.length === 0}
                >
                  {scheduling ? (
                    <Loader2 className="animate-spin" />
                  ) : (
                    "Add to queue"
                  )}
                </Button>
              </div>
            </div>
            {done && (
              <p className="rounded-md border border-emerald-500/40 bg-emerald-500/10 p-2 text-xs text-emerald-600">
                {done} It will fire when you approve it on /approve.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
