import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase-server";

export async function GET() {
  const { data, error } = await supabaseAdmin
    .from("scheduled")
    .select("*")
    .order("scheduled_for", { ascending: true });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ rows: data });
}

export async function POST(req: NextRequest) {
  const { content, scheduled_for } = (await req.json()) as {
    content: string;
    scheduled_for: string;
  };
  if (!content || !scheduled_for) {
    return NextResponse.json({ error: "content and scheduled_for required" }, { status: 400 });
  }
  const { data, error } = await supabaseAdmin
    .from("scheduled")
    .insert({ content, scheduled_for, status: "pending" })
    .select()
    .single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ row: data });
}

export async function PATCH(req: NextRequest) {
  const { id, status } = (await req.json()) as {
    id: string;
    status: "pending" | "approved" | "sent" | "failed";
  };
  if (!id || !status) {
    return NextResponse.json({ error: "id and status required" }, { status: 400 });
  }
  const { data, error } = await supabaseAdmin
    .from("scheduled")
    .update({ status })
    .eq("id", id)
    .select()
    .single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ row: data });
}
