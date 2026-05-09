import {
  convertToModelMessages,
  streamText,
  type UIMessage,
} from "ai";

export const maxDuration = 60;

const MODEL = process.env.AI_MODEL ?? "openai/gpt-5.4-mini";

const SYSTEM_PROMPT = `You are the launchpad assistant for "hackathon050926".

Your job is to help the team move fast:
- Brainstorm hackathon ideas and pivots.
- Sketch architectures (Next.js App Router, AI SDK, Vercel).
- Write small code snippets (TypeScript / React) that drop into this repo.
- Keep answers tight. Use short paragraphs, lists, and code blocks.

Be opinionated, candid, and a tiny bit playful. If asked to choose, choose.`;

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();

  const result = streamText({
    model: MODEL,
    system: SYSTEM_PROMPT,
    messages: await convertToModelMessages(messages),
  });

  return result.toUIMessageStreamResponse({
    onError: (error) => {
      console.error("[/api/chat] streamText error:", error);
      const message = error instanceof Error ? error.message : String(error);
      if (
        /gateway authentication|GatewayAuthentication|unauthori[sz]ed|api[_ -]?key/i.test(
          message,
        )
      ) {
        return "AI Gateway isn't configured yet. Add `AI_GATEWAY_API_KEY` to `.env.local` (or run `npx vercel link && vercel env pull`) — see the README for setup.";
      }
      return message || "Something went wrong while talking to the model.";
    },
  });
}
