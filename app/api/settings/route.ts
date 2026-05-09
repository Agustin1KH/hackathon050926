import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase-server";

export async function POST(req: NextRequest) {
  const body = (await req.json()) as Record<string, string>;
  const rows = Object.entries(body).map(([key, value]) => ({ key, value }));
  const { error } = await supabaseAdmin
    .from("config")
    .upsert(rows, { onConflict: "key" });
  if (error)
    return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true });
}
