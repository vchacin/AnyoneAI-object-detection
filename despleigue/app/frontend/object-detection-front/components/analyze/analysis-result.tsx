"use client";

import Link from "next/link";
import { formatMs, pct } from "@/lib/format";
import type { PredictResponse } from "@/lib/api/types";
import { usePrefs } from "@/stores/prefs-store";
import { Toggle } from "./toggle";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="tnum text-right font-medium">{children}</dd>
    </div>
  );
}

export function AnalysisResult({ result }: { result: PredictResponse }) {
  return (
    <div className="py-5">
      <div className="mb-3 flex items-end gap-6">
        <div>
          <p className="tnum text-3xl font-semibold tracking-tight text-gap">{result.n_missing}</p>
          <p className="text-xs text-muted-foreground">gaps</p>
        </div>
        <div>
          <p className="tnum text-3xl font-semibold tracking-tight">{result.n_objects}</p>
          <p className="text-xs text-muted-foreground">products</p>
        </div>
      </div>
      <dl className="divide-y divide-border/60">
        <Row label="Latency">{formatMs(result.latency_ms ?? result.timings.total_ms)}</Row>
        <Row label="Resolution">{result.width}×{result.height}</Row>
        <Row label="Model">{result.model_version}</Row>
        {result.gap_mode && <Row label="Gap mode">{result.gap_mode}</Row>}
        <Row label="Gap confidence (median)">{pct(result.confidence_summary.missing.median)}</Row>
        <Row label="Product confidence (median)">{pct(result.confidence_summary.objects.median)}</Row>
      </dl>
      {result.inspection_id && (
        <Link href={`/inspections?open=${result.inspection_id}`} className="mt-3 inline-block text-sm text-primary underline-offset-4 hover:underline">
          View saved inspection →
        </Link>
      )}
    </div>
  );
}

export function LayerToggles() {
  const prefs = usePrefs();
  return (
    <div className="pt-4">
      <p className="mb-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">Layers</p>
      <Toggle label="Products" checked={prefs.showObjects} onChange={(v) => prefs.set({ showObjects: v })} />
      <Toggle label="Gaps" checked={prefs.showMissing} onChange={(v) => prefs.set({ showMissing: v })} />
      <Toggle label="Box confidence" checked={prefs.showLabels} onChange={(v) => prefs.set({ showLabels: v })} />
    </div>
  );
}
