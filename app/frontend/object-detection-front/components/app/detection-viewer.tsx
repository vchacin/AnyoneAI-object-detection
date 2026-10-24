"use client";

import { cn } from "@/lib/utils";

export interface ViewerBox {
  box: [number, number, number, number];
  /** "missing" se resalta; cualquier otra clase se trata como producto presente. */
  kind: string;
  confidence: number;
}

interface DetectionViewerProps {
  src: string;
  width: number;
  height: number;
  boxes: ViewerBox[];
  showObjects?: boolean;
  showMissing?: boolean;
  showLabels?: boolean;
  className?: string;
}

/** Imagen con cajas superpuestas en SVG; escala con la imagen sin recalcular coordenadas. */
export function DetectionViewer({
  src,
  width,
  height,
  boxes,
  showObjects = true,
  showMissing = true,
  showLabels = false,
  className,
}: DetectionViewerProps) {
  const font = Math.max(10, width / 70);
  return (
    <div
      className={cn("relative mx-auto overflow-hidden rounded-md bg-muted", className)}
      style={{ width: `min(100%, calc(72vh * ${width / height}))`, aspectRatio: `${width} / ${height}` }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt="Imagen analizada" className="absolute inset-0 size-full object-fill" draggable={false} />
      <svg viewBox={`0 0 ${width} ${height}`} className="absolute inset-0 size-full" preserveAspectRatio="none">
        {boxes.map((b, i) => {
          const missing = b.kind === "missing";
          if (missing ? !showMissing : !showObjects) return null;
          const [x1, y1, x2, y2] = b.box;
          return (
            <g key={i}>
              <rect
                x={x1}
                y={y1}
                width={x2 - x1}
                height={y2 - y1}
                vectorEffect="non-scaling-stroke"
                strokeWidth={missing ? 2 : 1.25}
                strokeDasharray={missing ? "5 3" : undefined}
                className={cn(missing ? "fill-gap/25 stroke-gap" : "fill-info/5 stroke-info")}
              />
              {showLabels && (
                <text
                  x={x1 + 2}
                  y={Math.max(font, y1 - 2)}
                  fontSize={font}
                  className={cn("font-mono", missing ? "fill-gap" : "fill-info")}
                  stroke="black"
                  strokeWidth={font / 6}
                  paintOrder="stroke"
                >
                  {Math.round(b.confidence * 100)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
