"use client";

import { QueryBoundary } from "@/components/common/query-boundary";
import { RowsSkeleton } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { useHealth } from "@/hooks/queries/use-system";
import { StatusDot } from "./status-dot";

export function StatusTab() {
  const health = useHealth();
  return (
    <QueryBoundary query={health} skeleton={<RowsSkeleton rows={6} />}>
      {(h) => {
        const rows: [string, React.ReactNode][] = [
          ["Service", <><StatusDot ok={h.status === "ok"} />{h.status}</>],
          [h.inference_backend === "lambda" ? "Remote inference" : "Model loaded", <><StatusDot ok={h.model_loaded} />{h.model_loaded ? "Available" : h.inference_backend === "lambda" ? "Pending or unavailable" : "Loads on first inference"}</>],
          ["Model version", h.model_version ?? "—"],
          ["SHA-256", <span key="s" className="font-mono text-xs">{h.model_sha256 ?? "—"}</span>],
          ["Device", h.device ?? "—"],
          ["Input size", h.imgsz ? `${h.imgsz}px` : "—"],
          ["Database", h.database],
          ["Authentication", h.auth_required ? "Required" : "Disabled"],
        ];
        return (
          <div className="max-w-xl">
            <dl className="divide-y">
              {rows.map(([k, v]) => (
                <div key={k} className="flex justify-between gap-6 py-3 text-sm">
                  <dt className="text-muted-foreground">{k}</dt>
                  <dd className="text-right font-medium">{v}</dd>
                </div>
              ))}
            </dl>
            <Button variant="outline" size="sm" className="mt-4" onClick={() => void health.refetch()}>Actualizar</Button>
          </div>
        );
      }}
    </QueryBoundary>
  );
}
