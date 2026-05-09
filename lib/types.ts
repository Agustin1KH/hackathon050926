// Mirrors db/schema.sql — keep in sync.
// (Replace with `supabase gen types typescript` output once the project is provisioned.)

export type DraftRow = {
  id: string;
  topic: string | null;
  content: string;
  variant_index: number | null;
  created_at: string;
};

export type ScheduledStatus = "pending" | "approved" | "sent" | "failed";

export type ScheduledRow = {
  id: string;
  content: string;
  scheduled_for: string;
  status: ScheduledStatus;
  draft_id: string | null;
  created_at: string;
};

export type SentLogRow = {
  id: string;
  x_tweet_id: string | null;
  content: string;
  sent_at: string;
};

export type MentionStatus =
  | "new"
  | "drafted"
  | "approved"
  | "replied"
  | "skipped"
  | "spam";

export type MentionRow = {
  id: string;
  x_id: string;
  author: string | null;
  text: string | null;
  fetched_at: string;
  status: MentionStatus;
};

export type ReplyStatus = "pending" | "approved" | "sent";

export type ReplyRow = {
  id: string;
  mention_id: string | null;
  draft_content: string;
  status: ReplyStatus;
  created_at: string;
};

export type ConfigRow = {
  key: string;
  value: string | null;
};

export type AudienceSegment =
  | "developers"
  | "founders"
  | "marketers"
  | "designers"
  | "investors"
  | "creators"
  | "students"
  | "other";

export type AudienceRow = {
  id: string;
  follower_id: string;
  username: string | null;
  name: string | null;
  bio: string | null;
  follower_cnt: number | null;
  segment: AudienceSegment | null;
  segment_conf: number | null;
  fetched_at: string;
};
