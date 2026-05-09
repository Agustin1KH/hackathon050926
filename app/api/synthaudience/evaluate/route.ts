import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy to the teammate's synthaudience FastAPI service.
 * Atlas posts a draft tweet here; we forward it as a ContentPayload and
 * return the EvaluationReport so the dashboard can render scores per segment.
 *
 * Run synthaudience locally:
 *   uv run uvicorn synthaudience.api:app --reload   # port 8000
 */

export async function POST(req: NextRequest) {
  const { content, title } = (await req.json()) as {
    content: string;
    title?: string;
  };
  if (!content) {
    return NextResponse.json({ error: "content required" }, { status: 400 });
  }

  const url = process.env.SYNTHAUDIENCE_URL ?? "http://localhost:8000";

  const payload = {
    // synthaudience supports "instagram_post" | "video_script" | "ad_copy" | "video".
    // ad_copy is the closest analog to a tweet (short marketing/voice copy).
    kind: "ad_copy",
    title: title || content.slice(0, 60),
    body: content,
    media_description: null,
  };

  let res: Response;
  try {
    res = await fetch(`${url}/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    return NextResponse.json(
      {
        error: `synthaudience unreachable at ${url}. Is uvicorn running?`,
        detail: e instanceof Error ? e.message : String(e),
      },
      { status: 502 },
    );
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    return NextResponse.json(
      { error: `synthaudience returned ${res.status}`, detail: text },
      { status: 502 },
    );
  }

  const json = await res.json();

  // synthaudience returns { run_id }. Fetch the report so the UI gets data
  // back in one call.
  const runId = json.run_id;
  if (!runId) return NextResponse.json(json);

  const reportRes = await fetch(`${url}/reports/${runId}`);
  if (!reportRes.ok) {
    return NextResponse.json(json); // fall back to bare run_id
  }
  const report = await reportRes.json();
  return NextResponse.json(report);
}
