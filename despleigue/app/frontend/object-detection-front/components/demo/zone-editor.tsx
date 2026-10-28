"use client";

import { useRef, useState } from "react";
import { SquareDashed, Trash2, Upload, ZoomIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ImageLightbox } from "@/components/demo/image-lightbox";
import { resizedZone } from "@/lib/zones";
import { useZones, type Zone } from "@/stores/zones-store";

interface ZoneEditorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Primera capture subida del día; sirve como imagen de referencia. */
  reference?: string | null;
}

type Pt = { x: number; y: number };
const handles = [
  { id: "nw", label: "top-left corner", x: 0, y: 0, cursor: "nwse-resize" },
  { id: "n", label: "top edge", x: 50, y: 0, cursor: "ns-resize" },
  { id: "ne", label: "top-right corner", x: 100, y: 0, cursor: "nesw-resize" },
  { id: "e", label: "right edge", x: 100, y: 50, cursor: "ew-resize" },
  { id: "se", label: "bottom-right corner", x: 100, y: 100, cursor: "nwse-resize" },
  { id: "s", label: "bottom edge", x: 50, y: 100, cursor: "ns-resize" },
  { id: "sw", label: "bottom-left corner", x: 0, y: 100, cursor: "nesw-resize" },
  { id: "w", label: "left edge", x: 0, y: 50, cursor: "ew-resize" },
] as const;

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const rectFrom = (a: Pt, b: Pt) => ({
  x: Math.min(a.x, b.x),
  y: Math.min(a.y, b.y),
  w: Math.abs(a.x - b.x),
  h: Math.abs(a.y - b.y),
});
const pct = (z: Zone) => ({
  left: `${z.x * 100}%`,
  top: `${z.y * 100}%`,
  width: `${z.w * 100}%`,
  height: `${z.h * 100}%`,
});

/**
 * Editor simple de segmentos: se dibuja un rectángulo por segmento sobre la
 * imagen de referencia de la camera. Las coordenadas se guardan normalizadas
 * (0–1), así valen para cualquier resolución de capture.
 */
export function ZoneEditor({ open, onOpenChange, reference }: ZoneEditorProps) {
  const { zones, labels, addZone, addLabel, updateLabel, assignLabel, resizeZone, removeZone } = useZones();
  const [newLabel, setNewLabel] = useState("");
  const [customSrc, setCustomSrc] = useState<string | null>(null);
  const [draft, setDraft] = useState<Zone | null>(null);
  const [zoomOpen, setZoomOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const resizingRef = useRef<{ zone: Zone; handle: string } | null>(null);
  const drawingRef = useRef(false);
  const startRef = useRef<Pt | null>(null);
  const currentRef = useRef<Pt | null>(null);
  const src = customSrc ?? reference ?? null;

  const toPoint = (e: React.PointerEvent): Pt => {
    const r = canvasRef.current!.getBoundingClientRect();
    return { x: clamp01((e.clientX - r.left) / r.width), y: clamp01((e.clientY - r.top) / r.height) };
  };

  const handleDown = (e: React.PointerEvent) => {
    if (!src) return;
    setSelectedId(null);
    const p = toPoint(e);
    drawingRef.current = true;
    startRef.current = p;
    currentRef.current = p;
    setDraft({ id: "draft", name: "", labelId: "", ...rectFrom(p, p) });
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch {
      /* sin capture el puntero puede salirse del lienzo; handleMove allows eso */
    }
  };

  const handleMove = (e: React.PointerEvent) => {
    if (resizingRef.current) {
      const { zone, handle } = resizingRef.current;
      const next = { ...zone, ...resizedZone(zone, handle, toPoint(e)) };
      setDraft(next);
      return;
    }
    if (!drawingRef.current || !startRef.current) return;
    const p = toPoint(e);
    currentRef.current = p;
    setDraft({ id: "draft", name: "", labelId: "", ...rectFrom(startRef.current, p) });
  };

  const handleUp = (e: React.PointerEvent) => {
    if (resizingRef.current) {
      const { zone, handle } = resizingRef.current;
      const rect = resizedZone(zone, handle, toPoint(e));
      resizingRef.current = null;
      setDraft(null);
      resizeZone(zone.id, rect);
      return;
    }
    if (!drawingRef.current) return;
    drawingRef.current = false;
    const a = startRef.current;
    startRef.current = null;
    currentRef.current = null;
    setDraft(null);
    if (!a) return;
    const r = rectFrom(a, toPoint(e));
    if (r.w < 0.02 || r.h < 0.02) return; // click suelto, no un rectángulo
    addZone({ ...r, name: `Segment ${zones.length + 1}` });
  };

  const handleCancel = () => {
    resizingRef.current = null;
    drawingRef.current = false;
    startRef.current = null;
    setDraft(null);
  };

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCustomSrc((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return URL.createObjectURL(file);
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent lang="en" className="max-h-[95vh] overflow-y-auto sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>Shelf segments</DialogTitle>
          <DialogDescription>
            Drag on the reference image to draw a rectangle for each segment (e.g. Bonafont
            600 ml). Select a segment and drag its handles to adjust it. You can also choose
            a reusable label from the list. Changes are saved in this browser.
          </DialogDescription>
        </DialogHeader>

        <div
          ref={canvasRef}
          onPointerDown={handleDown}
          onPointerMove={handleMove}
          onPointerUp={handleUp}
          onPointerCancel={handleCancel}
          className={`relative w-full touch-none select-none overflow-hidden rounded-lg border border-border bg-muted ${
            src ? "cursor-crosshair" : ""
          }`}
        >
          {src ? (
            <img src={src} alt="Reference image" className="block w-full" draggable={false} />
          ) : (
            <div className="grid h-56 place-items-center text-sm text-muted-foreground">
              Choose a reference image to start drawing
            </div>
          )}
          {zones.map((original) => {
            const z = draft?.id === original.id ? draft : original;
            const selected = selectedId === z.id;
            return (
            <div
              key={z.id}
              style={{ ...pct(z), zIndex: selected ? 10 : undefined }}
              onPointerDown={(e) => {
                e.stopPropagation();
                setSelectedId(z.id);
              }}
              className="absolute cursor-pointer rounded-sm border-2 border-dashed border-primary bg-primary/5"
            >
              <span className="absolute top-0 left-0 max-w-full truncate rounded-br bg-primary px-1 py-0.5 text-[10px] font-medium text-primary-foreground">
                {z.name}
              </span>
              {selected && handles.map((handle) => (
                <button
                  key={handle.id}
                  type="button"
                  aria-label={`Adjust ${handle.label} of ${z.name}`}
                  style={{ left: `${handle.x}%`, top: `${handle.y}%`, cursor: handle.cursor }}
                  className="absolute size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-primary bg-white shadow focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                  onPointerDown={(e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    resizingRef.current = { zone: z, handle: handle.id };
                    canvasRef.current?.setPointerCapture(e.pointerId);
                  }}
                  onKeyDown={(e) => {
                    const dx = e.key === "ArrowLeft" ? -0.01 : e.key === "ArrowRight" ? 0.01 : 0;
                    const dy = e.key === "ArrowUp" ? -0.01 : e.key === "ArrowDown" ? 0.01 : 0;
                    if (!dx && !dy) return;
                    e.preventDefault();
                    const x = handle.id.includes("w") ? z.x : z.x + z.w;
                    const y = handle.id.includes("n") ? z.y : z.y + z.h;
                    resizeZone(z.id, resizedZone(z, handle.id, { x: x + dx, y: y + dy }));
                  }}
                />
              ))}
            </div>
          ); })}
          {draft?.id === "draft" && (
            <div
              style={pct(draft)}
              className="pointer-events-none absolute rounded-sm border-2 border-dashed border-info bg-info/10"
            />
          )}
          {src && (
            <div className="absolute bottom-2 left-2">
              <Button
                type="button"
                size="xs"
                variant="secondary"
                className="shadow"
                // stopPropagation: sin esto el clic del zoom empieza un dibujo
                onPointerDown={(e) => e.stopPropagation()}
                onClick={() => setZoomOpen(true)}
              >
                <ZoomIn className="size-3" />
                Zoom
              </Button>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <input
              id="zone-ref-upload"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              onChange={handleFile}
            />
            {/* Botón dentro de <label>: la etiqueta no reenvía clics a contenido
                interactive, así que el botón dispara el input directamente. */}
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => document.getElementById("zone-ref-upload")?.click()}
            >
              <Upload className="size-3.5" />
              {src ? "Change reference" : "Choose reference"}
            </Button>
          </div>
          <span className="text-xs text-muted-foreground">
            {zones.length} segment{zones.length === 1 ? "" : "s"}
          </span>
        </div>

        <div className="max-h-44 space-y-2 overflow-y-auto">
          {zones.length === 0 && (
            <p className="text-sm text-muted-foreground">No segments have been drawn yet.</p>
          )}
          {zones.map((z, i) => (
            <div key={z.id} className="flex items-center gap-2">
              <span className="tnum w-6 shrink-0 text-xs text-muted-foreground">{i + 1}.</span>
              <select
                value={z.labelId}
                onFocus={() => setSelectedId(z.id)}
                onChange={(e) => assignLabel(z.id, e.target.value)}
                aria-label={`Label for segment ${i + 1}`}
                className="h-8 min-w-0 flex-1 rounded-lg border border-border bg-background px-2 text-sm focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
              >
                {labels.map((label) => <option key={label.id} value={label.id}>{label.name || "Unnamed"}</option>)}
              </select>
              <Button
                type="button"
                size="icon-sm"
                variant="ghost"
                onClick={() => removeZone(z.id)}
                aria-label={`Delete ${z.name}`}
              >
                <Trash2 className="size-4 text-muted-foreground" />
              </Button>
            </div>
          ))}
        </div>

        <div className="space-y-3 border-t border-border pt-3">
          <div>
            <h3 className="text-sm font-semibold">Labels and financial details</h3>
            <p className="text-xs text-muted-foreground">A label shares its price and margin across all its segments. Margin is a percentage of the sale price.</p>
          </div>
          <div className="flex gap-2">
            <input value={newLabel} onChange={(e) => setNewLabel(e.target.value)} aria-label="New label name" placeholder="New label, e.g. Bonafont 600 ml" className="h-9 min-w-0 flex-1 rounded-lg border border-border bg-background px-2 text-sm" />
            <Button type="button" variant="outline" size="sm" disabled={!newLabel.trim() || labels.some((label) => label.name.trim().toLowerCase() === newLabel.trim().toLowerCase())} onClick={() => { addLabel(newLabel.trim()); setNewLabel(""); }}>Create label</Button>
          </div>
          <div className="max-h-56 space-y-2 overflow-y-auto">
            {labels.map((label) => (
              <div key={label.id} className="grid gap-2 rounded-lg border border-border p-2 sm:grid-cols-[minmax(0,1fr)_140px_140px]">
                <label className="grid gap-1 text-xs text-muted-foreground">Label
                  <input value={label.name} onChange={(e) => updateLabel(label.id, { name: e.target.value })} className="h-8 min-w-0 rounded-md border border-border bg-background px-2 text-sm text-foreground" />
                </label>
                <label className="grid gap-1 text-xs text-muted-foreground">Sale price (MXN)
                  <input type="number" min="0" step="any" inputMode="decimal" value={label.unitPrice} onChange={(e) => updateLabel(label.id, { unitPrice: e.target.value })} placeholder="No price" className="h-8 min-w-0 rounded-md border border-border bg-background px-2 text-sm text-foreground" />
                </label>
                <label className="grid gap-1 text-xs text-muted-foreground">Sales margin (%)
                  <input type="number" min="0" max="100" step="any" inputMode="decimal" value={label.margin} onChange={(e) => updateLabel(label.id, { margin: e.target.value })} placeholder="Optional" className="h-8 min-w-0 rounded-md border border-border bg-background px-2 text-sm text-foreground" />
                </label>
              </div>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            <SquareDashed className="size-4" />
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
      {src && (
        <ImageLightbox
          src={src}
          alt="Enlarged reference image"
          open={zoomOpen}
          onOpenChange={setZoomOpen}
        >
          <div className="pointer-events-none absolute inset-0">
            {zones.map((z) => (
              <div
                key={z.id}
                style={pct(z)}
                className="absolute rounded-sm border-2 border-dashed border-primary bg-primary/5"
              >
                <span className="absolute top-0 left-0 max-w-full truncate rounded-br bg-primary px-1 py-0.5 text-[10px] font-medium text-primary-foreground">
                  {z.name}
                </span>
              </div>
            ))}
          </div>
        </ImageLightbox>
      )}
    </Dialog>
  );
}
