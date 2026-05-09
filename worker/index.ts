/**
 * Background worker — runs alongside Next.js in dev or as a separate process
 * in prod. Polls Supabase for approved scheduled posts and approved replies,
 * fires them via the X API, marks them sent.
 *
 * Run:   npm run worker
 * Dev:   npm run worker:dev   (auto-reloads via tsx watch)
 */

import "dotenv/config";
import cron from "node-cron";
import { supabaseAdmin } from "../lib/supabase-server";
import { postTweet, replyTo, getMe, getMentions } from "../lib/x-client";

let myUserId: string | null = null;

async function ensureMe() {
  if (myUserId) return myUserId;
  const me = await getMe();
  myUserId = me.id;
  await supabaseAdmin.from("config").upsert([
    { key: "x_user_id", value: me.id },
    { key: "x_username", value: me.username },
  ]);
  return myUserId;
}

async function firePosts() {
  const nowIso = new Date().toISOString();
  const { data: due } = await supabaseAdmin
    .from("scheduled")
    .select("*")
    .eq("status", "approved")
    .lte("scheduled_for", nowIso);
  if (!due?.length) return;

  for (const row of due) {
    try {
      console.log(`[posts] firing ${row.id}: ${row.content.slice(0, 60)}…`);
      const tweet = await postTweet(row.content);
      await supabaseAdmin.from("scheduled").update({ status: "sent" }).eq("id", row.id);
      await supabaseAdmin.from("sent_log").insert({
        x_tweet_id: tweet.id,
        content: row.content,
      });
      console.log(`[posts] sent ${tweet.id}`);
    } catch (err) {
      console.error(`[posts] failed ${row.id}:`, err);
      await supabaseAdmin.from("scheduled").update({ status: "failed" }).eq("id", row.id);
    }
  }
}

async function fireReplies() {
  const { data: replies } = await supabaseAdmin
    .from("replies")
    .select("*, mentions(x_id)")
    .eq("status", "approved");
  if (!replies?.length) return;

  for (const r of replies) {
    const mention = (r as { mentions?: { x_id: string } }).mentions;
    if (!mention?.x_id) continue;
    try {
      console.log(`[replies] firing reply to ${mention.x_id}`);
      await replyTo(mention.x_id, r.draft_content);
      await supabaseAdmin.from("replies").update({ status: "sent" }).eq("id", r.id);
      await supabaseAdmin
        .from("mentions")
        .update({ status: "replied" })
        .eq("id", r.mention_id);
    } catch (err) {
      console.error(`[replies] failed ${r.id}:`, err);
    }
  }
}

async function pollMentions() {
  try {
    const userId = await ensureMe();
    // Get the most recent mention we've seen for `since_id`.
    const { data: latest } = await supabaseAdmin
      .from("mentions")
      .select("x_id")
      .order("fetched_at", { ascending: false })
      .limit(1);
    const sinceId = latest?.[0]?.x_id;

    const res = await getMentions(userId, sinceId);
    const tweets = res.data.data ?? [];
    if (!tweets.length) return;

    const usersById = new Map(
      (res.data.includes?.users ?? []).map((u) => [u.id, u]),
    );
    const rows = tweets.map((t) => ({
      x_id: t.id,
      author: usersById.get(t.author_id ?? "")?.username ?? null,
      text: t.text,
      status: "new",
    }));
    await supabaseAdmin.from("mentions").upsert(rows, { onConflict: "x_id" });
    console.log(`[mentions] fetched ${rows.length} new`);
  } catch (err) {
    console.error("[mentions] poll failed:", err);
  }
}

async function tick() {
  await Promise.all([firePosts(), fireReplies()]);
}

console.log("worker starting…");
ensureMe()
  .then((id) => console.log(`worker: authed as user ${id}`))
  .catch((err) => console.error("worker auth check failed:", err));

cron.schedule("* * * * *", () => {
  void tick();
});
cron.schedule("*/5 * * * *", () => {
  void pollMentions();
});

// Run once on boot.
void tick();
void pollMentions();
