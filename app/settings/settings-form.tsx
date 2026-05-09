"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Loader2 } from "lucide-react";

export function SettingsForm(props: {
  styleProfile: string;
  postSchedule: string;
  phoneNumber: string;
  xUsername: string;
}) {
  const router = useRouter();
  const [styleProfile, setStyle] = useState(props.styleProfile);
  const [postSchedule, setSchedule] = useState(props.postSchedule);
  const [phoneNumber, setPhone] = useState(props.phoneNumber);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function save() {
    setBusy(true);
    setDone(false);
    await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        style_profile: styleProfile,
        post_schedule: postSchedule,
        phone_number: phoneNumber,
      }),
    });
    setBusy(false);
    setDone(true);
    router.refresh();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Voice & cadence</CardTitle>
        <CardDescription>
          {props.xUsername
            ? `Connected to X as @${props.xUsername}`
            : "Not yet authenticated against X — set the env vars and refresh."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Field label="Voice profile" hint="Drives how every draft sounds.">
          <Textarea
            value={styleProfile}
            onChange={(e) => setStyle(e.target.value)}
            rows={3}
            placeholder="casual, technical, no hashtags, concise"
            className="font-mono text-sm"
          />
        </Field>
        <Field label="Post schedule" hint="Comma-separated 24h times for the daily slots.">
          <Input
            value={postSchedule}
            onChange={(e) => setSchedule(e.target.value)}
            placeholder="09:00,13:00,18:00"
            className="font-mono"
          />
        </Field>
        <Field label="Phone number" hint="E.164 format. Used for SMS approval (optional).">
          <Input
            value={phoneNumber}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+14155551234"
            className="font-mono"
          />
        </Field>
        <div className="flex items-center justify-end gap-3">
          {done && <span className="text-xs text-emerald-500">Saved.</span>}
          <Button onClick={save} disabled={busy}>
            {busy ? <Loader2 className="animate-spin" /> : "Save"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium">{label}</span>
      {children}
      <span className="text-[11px] text-muted-foreground">{hint}</span>
    </label>
  );
}
