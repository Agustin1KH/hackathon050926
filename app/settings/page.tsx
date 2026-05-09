import { supabaseAdmin } from "@/lib/supabase-server";
import { SettingsForm } from "./settings-form";

export const dynamic = "force-dynamic";
export const metadata = { title: "Settings" };

export default async function SettingsPage() {
  const { data } = await supabaseAdmin.from("config").select("*");
  const map: Record<string, string> = {};
  for (const row of data ?? []) {
    if (row.value != null) map[row.key as string] = row.value as string;
  }

  return (
    <>
      <header className="flex flex-col gap-1">
        <h1 className="font-heading text-3xl font-semibold tracking-tight">
          Settings
        </h1>
        <p className="text-sm text-muted-foreground">
          Voice profile and posting cadence. These shape every draft.
        </p>
      </header>
      <SettingsForm
        styleProfile={map.style_profile ?? ""}
        postSchedule={map.post_schedule ?? ""}
        phoneNumber={map.phone_number ?? ""}
        xUsername={map.x_username ?? ""}
      />
    </>
  );
}
