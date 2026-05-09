import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceKey = process.env.SUPABASE_SERVICE_KEY;

if (!url) throw new Error("NEXT_PUBLIC_SUPABASE_URL not set");
if (!serviceKey) throw new Error("SUPABASE_SERVICE_KEY not set");

export const supabaseAdmin = createClient(url, serviceKey, {
  auth: { persistSession: false, autoRefreshToken: false },
});
