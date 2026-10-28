"use client";

import { useState } from "react";
import { Upload, ZoomIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { ImageLightbox } from "@/components/demo/image-lightbox";
import { cn } from "@/lib/utils";
import { missingInZone } from "@/lib/zones";
import type { DemoAnalysisResult, CaptureSlot } from "@/services/demo.service";
import type { Zone } from "@/stores/zones-store";

interface DemoTimelineProps {
  slots: CaptureSlot[];
  previews: Record<string, string | null>;
  results?: Record<string, DemoAnalysisResult>;
  errors?: Record<string, string>;
  zones?: Zone[];
  onUpload: (id: string, file: File) => void;
}

function summary(result?: DemoAnalysisResult, error?: string) {
  if (!result) return error ?? "Analysis pending";
  if (result.nMissing > 0) return `${result.nObjects} products · ${result.nMissing} gaps detected`;
  return `${result.nObjects} products · no gaps detected`;
}

/**
 * Capa de segmentos + cajas de out of stock (coords relativas a la imagen).
 * Rojo: el gap cubre al menos el 60 % del segmento tras descontar products.
 * Amarillo: la caja original de "Empty" devuelta por el modelo.
 */
type Layers = { labels: boolean; missing: boolean; zones: boolean };

function LayerControls({ layers, setLayers, dark = false }: { layers: Layers; setLayers: React.Dispatch<React.SetStateAction<Layers>>; dark?: boolean }) {
  const options = [
    { key: "labels", label: "Labels" },
    { key: "missing", label: "Gap boxes" },
    { key: "zones", label: "Segment boxes" },
  ] as const;
  return (
    <div role="group" aria-label="Image layers" className={cn("flex flex-wrap items-center gap-x-5 gap-y-2 text-xs", dark ? "px-2 pt-2 text-white" : "mb-3 text-muted-foreground")}>
      {options.map(({ key, label }) => (
        <label key={key} className="flex cursor-pointer items-center gap-2">
          <Switch size="sm" checked={layers[key]} onCheckedChange={(checked) => setLayers((prev) => ({ ...prev, [key]: checked }))} />
          {label}
        </label>
      ))}
    </div>
  );
}

function Overlays({ result, zones, layers }: { result?: DemoAnalysisResult; zones: Zone[]; layers: Layers }) {
  const missingIn = (z: Zone) =>
    !!result &&
    result.missing.some((b) => missingInZone(b, result.width, result.height, z, result.objects));

  return (
    <div className="pointer-events-none absolute inset-0">
      {layers.zones && zones.map((z) => (
        <div
          key={z.id}
          style={{
            left: `${z.x * 100}%`,
            top: `${z.y * 100}%`,
            width: `${z.w * 100}%`,
            height: `${z.h * 100}%`,
          }}
          className={cn(
            "absolute rounded-sm border border-dashed bg-primary/5",
            missingIn(z) ? "border-destructive bg-destructive/5" : "border-primary",
          )}
        >
          {layers.labels && <span
            className={cn(
              "absolute top-0 left-0 max-w-full truncate rounded-br px-1 text-[10px] font-medium text-primary-foreground",
              missingIn(z) ? "bg-destructive" : "bg-primary/90",
            )}
          >
            {z.name}
          </span>}
        </div>
      ))}
      {layers.missing && result && result.width > 0
        ? result.missing.map((b, i) => (
            <div
              key={i}
              style={{
                left: `${(b.box[0] / result.width) * 100}%`,
                top: `${(b.box[1] / result.height) * 100}%`,
                width: `${((b.box[2] - b.box[0]) / result.width) * 100}%`,
                height: `${((b.box[3] - b.box[1]) / result.height) * 100}%`,
              }}
              className="absolute rounded-sm border-2 border-dashed border-amber-500 bg-amber-400/10"
            >
              {layers.labels && <span className="absolute -bottom-4 left-0 rounded bg-amber-500 px-1 text-[9px] font-semibold whitespace-nowrap text-white">
                Empty
              </span>}
            </div>
          ))
        : null}
    </div>
  );
}

/** Rejilla 3x2 de captures por schedule (mockup depletion.png). */
export function DemoTimeline({ slots, previews, results, errors = {}, zones = [], onUpload }: DemoTimelineProps) {
  const [zoomId, setZoomId] = useState<string | null>(null);
  const [layers, setLayers] = useState<Layers>({ labels: true, missing: true, zones: true });
  const zoomSlot = slots.find((s) => s.id === zoomId);

  const handleFile = (slotId: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) {
      alert("Only JPG, PNG or WebP images are allowed");
      return;
    }
    onUpload(slotId, file);
  };

  return (
    <>
      <LayerControls layers={layers} setLayers={setLayers} />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {slots.map((slot) => {
          const preview = previews[slot.id];
          const result = results?.[slot.id];
          return (
            <div key={slot.id} className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
              <div className="flex items-center gap-2 px-3 py-2">
                <span className="tnum text-sm font-semibold">{slot.time}</span>
                <span className={cn("ml-auto text-xs font-medium", errors[slot.id] ? "text-destructive" : result?.nMissing ? "text-primary" : "text-muted-foreground")}>
                  {errors[slot.id] ? "Analysis error" : !result ? "Not analyzed" : result.nMissing ? "Gaps detected" : "No gaps detected"}
                </span>
              </div>
              <div className="relative border-t border-border bg-muted">
                {preview ? (
                  <img src={preview} alt={`Image ${slot.time}`} className="block w-full" />
                ) : (
                  <div className="grid aspect-[4/3] place-items-center text-muted-foreground">
                    <div className="text-center">
                      <Upload className="mx-auto mb-1 size-6 opacity-50" />
                      <span className="text-xs">Pending</span>
                    </div>
                  </div>
                )}
                {preview && <Overlays result={result} zones={zones} layers={layers} />}
                <div className="absolute bottom-2 left-2 flex gap-1.5">
                  {preview && (
                    <Button
                      type="button"
                      size="xs"
                      variant="secondary"
                      className="shadow"
                      onClick={() => setZoomId(slot.id)}
                      aria-label={`Enlarge image ${slot.time}`}
                    >
                      <ZoomIn className="size-3" />
                      Zoom
                    </Button>
                  )}
                </div>
                <div className="absolute right-2 bottom-2 flex gap-1.5">
                  <input
                    id={`demo-upload-${slot.id}`}
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    className="sr-only"
                    onChange={handleFile(slot.id)}
                  />
                  {/* El botón vive dentro del <label>, que por spec no reenvía clics
                      a contenido interactive: hay que disparar el input a mano. */}
                  <Button
                    type="button"
                    size="xs"
                    variant="secondary"
                    className="shadow"
                    onClick={() => document.getElementById(`demo-upload-${slot.id}`)?.click()}
                  >
                    <Upload className="size-3" />
                    {preview ? "Change" : "Upload"}
                  </Button>
                </div>
              </div>
              <div className="flex items-center justify-between gap-2 px-3 py-2">
                <p className="truncate text-xs text-muted-foreground" title={errors[slot.id]}>{summary(result, errors[slot.id])}</p>
                {result && result.nMissing > 0 && (
                  <span className="shrink-0 rounded-full bg-primary/10 px-1.5 py-0.5 text-[11px] font-semibold text-primary">
                    {result.nMissing} gaps
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {zoomSlot && previews[zoomSlot.id] && (
        <ImageLightbox
          src={previews[zoomSlot.id]!}
          alt={`Enlarged image ${zoomSlot.time}`}
          open
          controls={<LayerControls layers={layers} setLayers={setLayers} dark />}
          onOpenChange={(o) => {
            if (!o) setZoomId(null);
          }}
        >
          <Overlays result={results?.[zoomSlot.id]} zones={zones} layers={layers} />
        </ImageLightbox>
      )}
    </>
  );
}
