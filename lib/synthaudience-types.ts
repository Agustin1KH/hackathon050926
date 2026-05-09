// Mirrors src/synthaudience/models.py from the agent_simulator branch.

export type AgentScore = {
  agent_id: string;
  content_id: string;
  like_score: number; // 0-10
  engage_probability: number; // 0-1
  share_probability: number; // 0-1
  sentiment: "positive" | "neutral" | "negative";
  comment: string;
  suggestion: string;
};

export type SegmentReport = {
  avg_like_score?: number;
  avg_engage?: number;
  avg_share?: number;
  sentiment_dist?: Record<string, number>;
  count?: number;
};

export type EvaluationReport = {
  run_id: string;
  content_id: string;
  overall: SegmentReport;
  by_segment: Record<string, SegmentReport>;
  top_themes_positive: string[];
  top_themes_negative: string[];
  representative_comments: Array<{
    segment_id?: string;
    comment: string;
    sentiment?: "positive" | "neutral" | "negative";
  }>;
};
