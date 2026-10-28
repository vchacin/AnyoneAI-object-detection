"use client";

import { Loader2, ScanSearch } from "lucide-react";
import { Choice } from "@/components/common/choice";
import { Field } from "@/components/common/form";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { useCameras } from "@/hooks/queries/use-cameras";
import { useShelves } from "@/hooks/queries/use-shelves";
import { useModels } from "@/hooks/queries/use-system";
import { useStoreContext } from "@/hooks/use-store-context";
import { pct } from "@/lib/format";
import { usePrefs } from "@/stores/prefs-store";
import { Toggle } from "./toggle";

interface Props {
  canAnalyze: boolean;
  isAnalyzing: boolean;
  hasResult: boolean;
  cameraId: string;
  shelfId: string;
  onCamera: (id: string, shelfOfCamera?: string | null) => void;
  onShelf: (id: string) => void;
  onAnalyze: () => void;
}

export function AnalyzeControls({ canAnalyze, isAnalyzing, hasResult, cameraId, shelfId, onCamera, onShelf, onAnalyze }: Props) {
  const { storeId } = useStoreContext();
  const prefs = usePrefs();
  const models = useModels();
  const cameras = useCameras(storeId);
  const shelves = useShelves(storeId);

  const catalog = models.data;
  const active = catalog?.models.find((m) => m.name === (prefs.model || catalog.default_model));
  const autoConf = prefs.conf === null;
  const confValue = prefs.conf ?? active?.default_conf ?? 0.25;

  return (
    <div className="grid gap-4 pb-5">
      <Field label="Model">
        <Choice
          value={prefs.model}
          onChange={(v) => prefs.set({ model: v })}
          emptyLabel={`Active (${catalog?.default_model ?? "…"})`}
          options={(catalog?.models ?? []).map((m) => ({ value: m.name, label: m.available ? m.name : `${m.name} (no weights)` }))}
        />
      </Field>

      <Field label={`Confidence threshold · ${autoConf ? "auto" : pct(confValue)}`}>
        <Slider min={0.05} max={0.95} step={0.05} value={[confValue]} onValueChange={(v) => prefs.set({ conf: Array.isArray(v) ? v[0] : v })} />
        <button
          type="button"
          disabled={autoConf}
          onClick={() => prefs.set({ conf: null })}
          className="w-fit text-xs text-muted-foreground underline-offset-4 hover:text-foreground hover:underline disabled:no-underline disabled:opacity-60"
        >
          {autoConf ? `Using the model default (${pct(active?.default_conf)})` : "Reset to model default"}
        </button>
      </Field>

      {storeId && (
        <>
          <Field label="Camera">
            <Choice
              value={cameraId}
              onChange={(v) => onCamera(v, cameras.data?.find((c) => c.id === v)?.shelf_id)}
              emptyLabel="No camera"
              options={(cameras.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
            />
          </Field>
          <Field label="Shelf" hint="Selecting a shelf enables alerts when the gap threshold is exceeded.">
            <Choice
              value={shelfId}
              onChange={onShelf}
              emptyLabel="No shelf"
              options={(shelves.data ?? []).map((s) => ({ value: s.id, label: s.zone ? `${s.name} · ${s.zone}` : s.name }))}
            />
          </Field>
        </>
      )}

      <Toggle label="Save as inspection" checked={prefs.persist} onChange={(v) => prefs.set({ persist: v })} />

      <Button size="lg" className="h-9" disabled={!canAnalyze || isAnalyzing} onClick={onAnalyze}>
        {isAnalyzing ? <Loader2 className="animate-spin" /> : <ScanSearch />}
        {hasResult ? "Analyze again" : "Analyze"}
      </Button>
    </div>
  );
}
