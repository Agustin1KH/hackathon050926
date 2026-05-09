import { NextRequest, NextResponse } from "next/server";
import { anthropic, MODEL } from "@/lib/anthropic";
import { supabaseAdmin } from "@/lib/supabase-server";
import {
  SYSTEM_VOICE,
  DRAFT_REPLY_USER,
  audienceSummary,
} from "@/lib/prompts";
import type { AudienceSegment } from "@/lib/types";

export async function POST(req: NextRequest) {
  const { mentionId } = (await req.json()) as { mentionId: string };
  if (!mentionId) {
    return NextResponse.json({ error: "mentionId required" }, { status: 400 });
  }

  const { data: mention, error } = await supabaseAdmin
    .from("mentions")
    .select("*")
    .eq("id", mentionId)
    .single();
  if (error || !mention) {
    return NextResponse.json({ error: "mention not found" }, { status: 404 });
  }

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

  const msg = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 512,
    system: SYSTEM_VOICE(styleProfile),
    messages: [
      {
        role: "user",
        content: DRAFT_REPLY_USER({
          author: mention.author ?? "user",
          message: mention.text ?? "",
          audience: audienceSummary(segments),
        }),
      },
    ],
  });

  const text = msg.content
    .filter((b) => b.type === "text")
    .map((b) => (b as { text: string }).text)
    .join("\n");

  let drafts: string[] = [];
  try {
    drafts = JSON.parse(text);
  } catch {
    const m = text.match(/\[[\s\S]*\]/);
    if (m) drafts = JSON.parse(m[0]);
  }

  // Save first draft to replies table.
  if (drafts[0]) {
    await supabaseAdmin.from("replies").insert({
      mention_id: mentionId,
      draft_content: drafts[0],
      status: "pending",
    });
    await supabaseAdmin
      .from("mentions")
      .update({ status: "drafted" })
      .eq("id", mentionId);
  }

  return NextResponse.json({ drafts });
}
