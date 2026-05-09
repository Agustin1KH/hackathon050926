import { NextRequest, NextResponse } from "next/server";
import { anthropic, MODEL } from "@/lib/anthropic";
import { supabaseAdmin } from "@/lib/supabase-server";
import {
  SYSTEM_VOICE,
  DRAFT_POST_USER,
  audienceSummary,
} from "@/lib/prompts";
import type { AudienceSegment } from "@/lib/types";

export async function POST(req: NextRequest) {
  const { topic, n = 3 } = (await req.json()) as { topic: string; n?: number };
  if (!topic) {
    return NextResponse.json({ error: "topic required" }, { status: 400 });
  }

  // Pull style profile + audience snapshot from DB.
  const [styleRes, audienceRes] = await Promise.all([
    supabaseAdmin
      .from("config")
      .select("value")
      .eq("key", "style_profile")
      .maybeSingle(),
    supabaseAdmin.from("audience").select("segment"),
  ]);

  const styleProfile =
    styleRes.data?.value ?? "casual, technical, no hashtags, concise";

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
  for (const row of audienceRes.data ?? []) {
    const s = (row as { segment: AudienceSegment | null }).segment;
    if (s && s in segments) segments[s] += 1;
  }
  const audience = audienceSummary(segments);

  const msg = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 1024,
    system: SYSTEM_VOICE(styleProfile),
    messages: [{ role: "user", content: DRAFT_POST_USER({ topic, audience, n }) }],
  });

  const text = msg.content
    .filter((b) => b.type === "text")
    .map((b) => (b as { text: string }).text)
    .join("\n");

  let variants: string[] = [];
  try {
    variants = JSON.parse(text);
  } catch {
    // model included prose around the JSON; try extracting
    const m = text.match(/\[[\s\S]*\]/);
    if (m) variants = JSON.parse(m[0]);
  }

  return NextResponse.json({ variants, audience });
}
