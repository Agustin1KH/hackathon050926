import { NextResponse } from "next/server";
import { anthropic, MODEL } from "@/lib/anthropic";
import { supabaseAdmin } from "@/lib/supabase-server";
import { getFollowers, getMe } from "@/lib/x-client";
import {
  SEGMENT_FOLLOWERS_SYSTEM,
  SEGMENT_FOLLOWERS_USER,
} from "@/lib/prompts";

const SEGMENTS = [
  "developers",
  "founders",
  "marketers",
  "designers",
  "investors",
  "creators",
  "students",
  "other",
] as const;

async function classifyBio(bio: string) {
  const msg = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 64,
    system: SEGMENT_FOLLOWERS_SYSTEM,
    messages: [{ role: "user", content: SEGMENT_FOLLOWERS_USER(bio) }],
  });
  const text = msg.content
    .filter((b) => b.type === "text")
    .map((b) => (b as { text: string }).text)
    .join("\n");
  try {
    const obj = JSON.parse(text.match(/\{[\s\S]*\}/)?.[0] ?? "{}");
    const seg = SEGMENTS.includes(obj.segment) ? obj.segment : "other";
    const conf = typeof obj.confidence === "number" ? obj.confidence : 0.5;
    return { segment: seg, confidence: conf };
  } catch {
    return { segment: "other" as const, confidence: 0.3 };
  }
}

export async function POST() {
  const me = await getMe();
  await supabaseAdmin.from("config").upsert([
    { key: "x_user_id", value: me.id },
    { key: "x_username", value: me.username },
  ]);

  const followers = await getFollowers(me.id, 100); // cap for hackathon

  // Classify bios in parallel (limited concurrency to respect rate limits).
  const CONCURRENCY = 5;
  const results: {
    follower_id: string;
    username: string;
    name: string;
    bio: string;
    follower_cnt: number;
    segment: string;
    segment_conf: number;
  }[] = [];

  for (let i = 0; i < followers.length; i += CONCURRENCY) {
    const batch = followers.slice(i, i + CONCURRENCY);
    const segments = await Promise.all(batch.map((f) => classifyBio(f.bio)));
    batch.forEach((f, j) =>
      results.push({
        follower_id: f.id,
        username: f.username,
        name: f.name,
        bio: f.bio,
        follower_cnt: f.follower_cnt,
        segment: segments[j].segment,
        segment_conf: segments[j].confidence,
      }),
    );
  }

  if (results.length) {
    await supabaseAdmin
      .from("audience")
      .upsert(results, { onConflict: "follower_id" });
  }

  // Return summary for UI.
  const counts: Record<string, number> = {};
  for (const r of results) counts[r.segment] = (counts[r.segment] ?? 0) + 1;

  return NextResponse.json({
    total: results.length,
    segments: counts,
    user: { id: me.id, username: me.username, name: me.name },
  });
}
