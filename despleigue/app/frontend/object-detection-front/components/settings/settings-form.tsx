"use client";

import { Loader2 } from "lucide-react";
import { Field } from "@/components/common/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { useSettingsForm } from "@/hooks/use-settings-form";
import { useStoreContext } from "@/hooks/use-store-context";
import type { StoreSettings } from "@/lib/api/types";
import { pct } from "@/lib/format";

export function SettingsForm({ storeId, initial }: { storeId: string; initial: StoreSettings }) {
  const { canManage } = useStoreContext();
  const { draft: d, patch, save, saving } = useSettingsForm(storeId, initial);

  return (
    <form
      className="max-w-xl divide-y"
      onSubmit={(e) => {
        e.preventDefault();
        save();
      }}
    >
      <fieldset disabled={!canManage || saving} className="grid gap-5 pb-6">
        <legend className="mb-4 text-sm font-semibold">Schedule</legend>
        <Field label="Time zone" htmlFor="tz" hint="IANA name, for example America/Chicago.">
          <Input id="tz" value={d.timezone} onChange={(e) => patch({ timezone: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Opens at" htmlFor="open"><Input id="open" type="time" value={d.opening_time} onChange={(e) => patch({ opening_time: e.target.value })} /></Field>
          <Field label="Closes at" htmlFor="close"><Input id="close" type="time" value={d.closing_time} onChange={(e) => patch({ closing_time: e.target.value })} /></Field>
        </div>
        <Field label="Peak hours" htmlFor="peak" hint="Comma-separated ranges, for example 12:00–14:00, 18:00–20:00.">
          <Input id="peak" value={d.peak} onChange={(e) => patch({ peak: e.target.value })} />
        </Field>
      </fieldset>

      <fieldset disabled={!canManage || saving} className="grid gap-5 py-6">
        <legend className="mb-4 text-sm font-semibold">Detection and alerts</legend>
        <Field label={`Default confidence · ${pct(d.default_conf)}`} hint="Threshold used when an inspection does not specify one.">
          <Slider min={0.05} max={0.95} step={0.05} value={[d.default_conf]} onValueChange={(v) => patch({ default_conf: Array.isArray(v) ? v[0] : v })} />
        </Field>
        <Field label="Alert cooldown (minutes)" htmlFor="cool" hint="Minimum time between alerts for the same shelf. 0 disables the cooldown.">
          <Input id="cool" type="number" min={0} value={d.cooldown} onChange={(e) => patch({ cooldown: e.target.value })} className="w-32" />
        </Field>
      </fieldset>

      {canManage ? (
        <div className="pt-6">
          <Button type="submit" disabled={saving}>
            {saving && <Loader2 className="animate-spin" />} Save changes
          </Button>
        </div>
      ) : (
        <p className="pt-6 text-sm text-muted-foreground">Only administrators can change these settings.</p>
      )}
    </form>
  );
}
