import { NextRequest, NextResponse } from "next/server";
import { anthropic, MODEL } from "@/lib/anthropic";
import { supabaseAdmin } from "@/lib/supabase-server";
import {
  SYSTEM_VOICE,
  DRAFT_REPLY_USER,
  audienceSummary,
} from "@/lib/prompts";
import type { AudienceSegment } from "@/lib/types";

async function loadVoiceContext() {
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
  return { styleProfile, audience: audienceSummary(segments) };
}

// Generate (or regenerate) a reply draft for a given mention.
export async function POST(req: NextRequest) {
  const { mentionId } = (await req.json()) as { mentionId: string };
  if (!mentionId)
    return NextResponse.json({ error: "mentionId required" }, { status: 400 });

  const { data: mention, error } = await supabaseAdmin
    .from("mentions")
    .select("*")
    .eq("id", mentionId)
    .single();
  if (error || !mention)
    return NextResponse.json({ error: "mention not found" }, { status: 404 });

  const { styleProfile, audience } = await loadVoiceContext();

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
          audience,
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

  if (drafts[0]) {
    // Upsert: if we already drafted for this mention, replace.
    const existing = await supabaseAdmin
      .from("replies")
      .select("id")
      .eq("mention_id", mentionId)
      .maybeSingle();
    if (existing.data?.id) {
      await supabaseAdmin
        .from("replies")
        .update({ draft_content: drafts[0], status: "pending" })
        .eq("id", existing.data.id);
    } else {
      await supabaseAdmin.from("replies").insert({
        mention_id: mentionId,
        draft_content: drafts[0],
        status: "pending",
      });
    }
    await supabaseAdmin
      .from("mentions")
      .update({ status: "drafted" })
      .eq("id", mentionId);
  }

  return NextResponse.json({ drafts });
}

// Approve a reply (mark approved, optionally save edited content) OR mark a
// mention as skipped.
export async function PATCH(req: NextRequest) {
  const body = (await req.json()) as {
    id?: string;
    status?: "approved" | "sent";
    content?: string;
    mentionId?: string;
    mentionStatus?: "skipped" | "spam";
  };

  if (body.mentionId && body.mentionStatus) {
    await supabaseAdmin
      .from("mentions")
      .update({ status: body.mentionStatus })
      .eq("id", body.mentionId);
    return NextResponse.json({ ok: true });
  }

  if (body.id && body.status) {
    const update: Record<string, unknown> = { status: body.status };
    if (body.content) update.draft_content = body.content;
    const { data, error } = await supabaseAdmin
      .from("replies")
      .update(update)
      .eq("id", body.id)
      .select("mention_id")
      .single();
    if (error)
      return NextResponse.json({ error: error.message }, { status: 500 });
    // If approving, also flip the mention status to 'approved' so the worker
    // picks it up.
    if (body.status === "approved" && data?.mention_id) {
      await supabaseAdmin
        .from("mentions")
        .update({ status: "approved" })
        .eq("id", data.mention_id);
    }
    return NextResponse.json({ ok: true });
  }

  return NextResponse.json({ error: "invalid body" }, { status: 400 });
}
