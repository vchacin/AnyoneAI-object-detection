import type { Inspection } from "@/lib/api/types";
import { formatBytes, formatMs } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Props {
  inspection: Inspection;
  shelfName?: string;
  cameraName?: string;
}

export function InspectionDetails({ inspection: i, shelfName, cameraName }: Props) {
  const rows: [string, React.ReactNode][] = [
    ["Huecos", <span key="m" className={cn("font-semibold", i.n_missing > 0 && "text-gap")}>{i.n_missing}</span>],
    ["Productos", i.n_objects],
    ["Latencia", formatMs(i.latency_ms)],
    ["Estante", shelfName ?? "—"],
    ["Cámara", cameraName ?? "—"],
    ["Origen", i.source === "camera" ? "Cámara" : "Manual"],
    ["Modelo", i.model_version],
    ["Resolución", i.image_width ? `${i.image_width}×${i.image_height}` : "—"],
    ["Tamaño", formatBytes(i.image_bytes)],
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm sm:grid-cols-3">
      {rows.map(([k, v]) => (
        <div key={k}>
          <dt className="text-xs text-muted-foreground">{k}</dt>
          <dd className="tnum font-medium break-words">{v}</dd>
        </div>
      ))}
    </dl>
  );
}
