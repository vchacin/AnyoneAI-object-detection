"use client";

import { ImageOff, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";
import { DetectionViewer, type ViewerBox } from "@/components/app/detection-viewer";
import { Switch } from "@/components/ui/switch";
import { useInspectionImage } from "@/hooks/queries/use-inspections";
import type { Inspection } from "@/lib/api/types";

/** Imagen de la inspeccion con sus cajas y los interruptores de capas. */
export function InspectionImage({ inspection }: { inspection: Inspection }) {
  const image = useInspectionImage(inspection.id);
  const [showObjects, setShowObjects] = useState(true);
  const [showMissing, setShowMissing] = useState(true);

  const boxes = useMemo<ViewerBox[]>(
    () =>
      inspection.detections.map((d) => ({
        box: d.bbox,
        kind: d.class === "missing" ? "missing" : "object",
        confidence: d.confidence,
      })),
    [inspection.detections],
  );

  return (
    <div className="grid gap-4">
      {image.data && inspection.image_width && inspection.image_height ? (
        <DetectionViewer
          src={image.data}
          width={inspection.image_width}
          height={inspection.image_height}
          boxes={boxes}
          showObjects={showObjects}
          showMissing={showMissing}
        />
      ) : (
        <div className="grid aspect-video place-items-center rounded-md bg-muted text-muted-foreground">
          {image.isError ? (
            <span className="flex items-center gap-2 text-sm">
              <ImageOff className="size-4" /> Imagen no disponible
            </span>
          ) : (
            <Loader2 className="size-5 animate-spin" />
          )}
        </div>
      )}
      <div className="flex gap-6 text-sm">
        <label className="flex items-center gap-2">
          <Switch size="sm" checked={showObjects} onCheckedChange={setShowObjects} />
          <span className="inline-block size-2 rounded-sm bg-info" /> Productos
        </label>
        <label className="flex items-center gap-2">
          <Switch size="sm" checked={showMissing} onCheckedChange={setShowMissing} />
          <span className="inline-block size-2 rounded-sm bg-gap" /> Huecos
        </label>
      </div>
    </div>
  );
}
