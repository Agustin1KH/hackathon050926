import type { AudienceSegment } from "./types";

export const SYSTEM_VOICE = (styleProfile: string) => `\
You are a writing assistant that drafts X (Twitter) posts in the user's voice.

Voice profile:
${styleProfile}

Hard rules:
- Stay under 280 characters per tweet (count emoji as 2).
- No hashtags unless the voice profile explicitly allows them.
- No em dashes (—). Use commas, periods, or regular dashes.
- No corporate buzzwords ("synergy", "leverage", "ecosystem").
- First person, specific, concrete details > generic claims.
- Sound like a real person texting, not a press release.
`;

export const DRAFT_POST_USER = (params: {
  topic: string;
  audience: string;
  n: number;
}) => `\
Topic: ${params.topic}

Audience context: ${params.audience || "general followers"}

Generate ${params.n} distinct draft variants. Each should be a different shape:
1. A short punchy single tweet (one sentence, memorable).
2. A thread starter (first tweet of a 3-5 tweet thread, ends with a hook).
3. A contrarian or surprising take.

Return ONLY a JSON array of strings, no preamble. Example:
["draft 1", "draft 2", "draft 3"]
`;

export const DRAFT_REPLY_USER = (params: {
  author: string;
  message: string;
  audience: string;
}) => `\
Original message from @${params.author}:
"${params.message}"

Audience context: ${params.audience || "general followers"}

Draft up to 2 reply options that respond directly to the message in the user's
voice. Stay under 280 chars. Be substantive — avoid generic agreement.

Return ONLY a JSON array of strings.
`;

export const CLASSIFY_USER = (params: { author: string; message: string }) => `\
Classify this incoming message as exactly one of:
- spam          (promotional, bot, off-topic, unrelated)
- no_action     (a like-style "great post", emoji-only, no real engagement needed)
- reply_needed  (a real question, opinion, or thread worth engaging with)

Message from @${params.author}:
"${params.message}"

Reply with ONLY the label, no explanation.
`;

export const SEGMENT_FOLLOWERS_SYSTEM = `\
You classify X (Twitter) bios into audience segments. Be decisive — pick one.

Segments:
- developers   : engineers, programmers, devops, ML, infra
- founders     : startup founders, CEOs, building a company
- marketers    : growth, content, marketing, brand
- designers    : UX, UI, product designers, creative directors
- investors    : VCs, angels, fund managers
- creators     : writers, content creators, streamers, journalists
- students     : students, learners, juniors looking to break in
- other        : doesn't fit any of the above

Return JSON: {"segment": "<one>", "confidence": 0.0-1.0}
`;

export const SEGMENT_FOLLOWERS_USER = (bio: string) => `\
Bio: "${bio || "(empty)"}"
`;

export function audienceSummary(segments: Record<AudienceSegment, number>) {
  const total = Object.values(segments).reduce((a, b) => a + b, 0) || 1;
  const ranked = (Object.entries(segments) as [AudienceSegment, number][])
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([s, n]) => `${Math.round((n / total) * 100)}% ${s}`)
    .join(", ");
  return ranked || "general followers";
}
