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
        <legend className="mb-4 text-sm font-semibold">Horario</legend>
        <Field label="Zona horaria" htmlFor="tz" hint="Nombre IANA, por ejemplo America/Bogota.">
          <Input id="tz" value={d.timezone} onChange={(e) => patch({ timezone: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Apertura" htmlFor="open"><Input id="open" type="time" value={d.opening_time} onChange={(e) => patch({ opening_time: e.target.value })} /></Field>
          <Field label="Cierre" htmlFor="close"><Input id="close" type="time" value={d.closing_time} onChange={(e) => patch({ closing_time: e.target.value })} /></Field>
        </div>
        <Field label="Horas pico" htmlFor="peak" hint="Rangos separados por coma, por ejemplo 12:00-14:00, 18:00-20:00.">
          <Input id="peak" value={d.peak} onChange={(e) => patch({ peak: e.target.value })} />
        </Field>
      </fieldset>

      <fieldset disabled={!canManage || saving} className="grid gap-5 py-6">
        <legend className="mb-4 text-sm font-semibold">Detección y alertas</legend>
        <Field label={`Confianza por defecto · ${pct(d.default_conf)}`} hint="Umbral que se usa cuando una inspección no indica uno.">
          <Slider min={0.05} max={0.95} step={0.05} value={[d.default_conf]} onValueChange={(v) => patch({ default_conf: Array.isArray(v) ? v[0] : v })} />
        </Field>
        <Field label="Enfriamiento de alertas (minutos)" htmlFor="cool" hint="Tiempo mínimo entre alertas del mismo estante. 0 desactiva el enfriamiento.">
          <Input id="cool" type="number" min={0} value={d.cooldown} onChange={(e) => patch({ cooldown: e.target.value })} className="w-32" />
        </Field>
      </fieldset>

      {canManage ? (
        <div className="pt-6">
          <Button type="submit" disabled={saving}>
            {saving && <Loader2 className="animate-spin" />} Guardar cambios
          </Button>
        </div>
      ) : (
        <p className="pt-6 text-sm text-muted-foreground">Solo los administradores pueden modificar estos ajustes.</p>
      )}
    </form>
  );
}
