import { TwitterApi } from "twitter-api-v2";

const required = [
  "X_API_KEY",
  "X_API_SECRET",
  "X_ACCESS_TOKEN",
  "X_ACCESS_SECRET",
  "X_BEARER_TOKEN",
] as const;

function envOrThrow() {
  for (const k of required) {
    if (!process.env[k]) {
      throw new Error(`Missing ${k} in env. See .env.local.example.`);
    }
  }
}

export function userClient() {
  envOrThrow();
  return new TwitterApi({
    appKey: process.env.X_API_KEY!,
    appSecret: process.env.X_API_SECRET!,
    accessToken: process.env.X_ACCESS_TOKEN!,
    accessSecret: process.env.X_ACCESS_SECRET!,
  });
}

export function appClient() {
  if (!process.env.X_BEARER_TOKEN) throw new Error("Missing X_BEARER_TOKEN");
  return new TwitterApi(process.env.X_BEARER_TOKEN);
}

export async function postTweet(content: string) {
  const { data } = await userClient().v2.tweet(content);
  return data;
}

export async function replyTo(tweetId: string, content: string) {
  const { data } = await userClient().v2.reply(content, tweetId);
  return data;
}

export async function getMe() {
  const { data } = await userClient().v2.me();
  return data;
}

export async function getMentions(userId: string, sinceId?: string) {
  const res = await userClient().v2.userMentionTimeline(userId, {
    since_id: sinceId,
    max_results: 20,
    "tweet.fields": ["author_id", "created_at", "text"],
    "user.fields": ["username", "name"],
    expansions: ["author_id"],
  });
  return res;
}

export async function getFollowers(userId: string, max = 200) {
  const out: {
    id: string;
    username: string;
    name: string;
    bio: string;
    follower_cnt: number;
  }[] = [];

  const paginator = await userClient().v2.followers(userId, {
    asPaginator: true,
    max_results: 100,
    "user.fields": ["description", "public_metrics", "username", "name"],
  });

  for await (const u of paginator) {
    out.push({
      id: u.id,
      username: u.username,
      name: u.name,
      bio: u.description ?? "",
      follower_cnt: u.public_metrics?.followers_count ?? 0,
    });
    if (out.length >= max) break;
  }
  return out;
}
