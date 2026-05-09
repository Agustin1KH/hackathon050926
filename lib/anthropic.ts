import Anthropic from "@anthropic-ai/sdk";

if (!process.env.ANTHROPIC_API_KEY) {
  // Defer the throw until first use so the dashboard renders without the key.
  console.warn("ANTHROPIC_API_KEY is not set. AI routes will fail until you add it.");
}

export const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

export const MODEL = "claude-sonnet-4-6";
