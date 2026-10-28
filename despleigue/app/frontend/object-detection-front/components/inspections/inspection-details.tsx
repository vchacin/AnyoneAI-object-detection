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
    ["Gaps", <span key="m" className={cn("font-semibold", i.n_missing > 0 && "text-gap")}>{i.n_missing}</span>],
    ["Products", i.n_objects],
    ["Latency", formatMs(i.latency_ms)],
    ["Shelf", shelfName ?? "—"],
    ["Camera", cameraName ?? "—"],
    ["Source", i.source === "camera" ? "Camera" : "Manual"],
    ["Model", i.model_version],
    ["Resolution", i.image_width ? `${i.image_width}×${i.image_height}` : "—"],
    ["Size", formatBytes(i.image_bytes)],
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
