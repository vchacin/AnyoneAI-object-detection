"use client";

import { useState } from "react";
import { useUpdateSettings } from "@/hooks/queries/use-stores";
import type { StoreSettings } from "@/lib/api/types";

export interface SettingsDraft {
  timezone: string;
  opening_time: string;
  closing_time: string;
  peak: string;
  default_conf: number;
  cooldown: string;
}

const peakToText = (v: unknown[] | null) =>
  (v ?? []).map((x) => (typeof x === "string" ? x : JSON.stringify(x))).join(", ");

const toDraft = (s: StoreSettings): SettingsDraft => ({
  timezone: s.timezone,
  opening_time: s.opening_time ?? "",
  closing_time: s.closing_time ?? "",
  peak: peakToText(s.peak_hours),
  default_conf: s.default_conf,
  cooldown: String(s.alert_cooldown_minutes),
});

export function useSettingsForm(storeId: string, initial: StoreSettings) {
  const [draft, setDraft] = useState(() => toDraft(initial));
  const update = useUpdateSettings(storeId);

  return {
    draft,
    patch: (partial: Partial<SettingsDraft>) => setDraft((d) => ({ ...d, ...partial })),
    saving: update.isPending,
    save: () =>
      update.mutate({
        timezone: draft.timezone.trim() || undefined,
        opening_time: draft.opening_time || null,
        closing_time: draft.closing_time || null,
        peak_hours: draft.peak.split(",").map((x) => x.trim()).filter(Boolean),
        default_conf: draft.default_conf,
        alert_cooldown_minutes: Math.max(0, Number.parseInt(draft.cooldown, 10) || 0),
      }),
  };
}
