"use client";

import { useState } from "react";
import { Calendar, Download, FileText, Images, Play, SquareDashed, Zap } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { DemoBackendSelector } from "@/components/demo/demo-backend-selector";
import { DemoMetrics } from "@/components/demo/demo-metrics";
import { DemoReportDialog } from "@/components/demo/demo-report-dialog";
import { DemoTimeline } from "@/components/demo/demo-timeline";
import { ZoneEditor } from "@/components/demo/zone-editor";
import { DEMO_SLOTS, useDemo } from "@/hooks/use-demo";
import { computeInsights, recommend } from "@/lib/insights";
import { cn } from "@/lib/utils";
import { useZones } from "@/stores/zones-store";

const TONE: Record<"critical" | "warning" | "ok", string> = {
  critical: "text-primary",
  warning: "text-amber-600",
  ok: "text-ok",
};

function SummaryItem({ label, value, tone }: { label: string; value: string; tone?: "primary" }) {
  return (
    <div className="min-w-0">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={tone === "primary" ? "truncate text-sm font-semibold text-primary" : "truncate text-sm font-medium"}>
        {value}
      </p>
    </div>
  );
}

export default function DemoPage() {
  const {
    provider,
    setProvider,
    settingsBusy,
    settingsMessage,
    saveSettings,
    confidence,
    setConfidence,
    iou,
    setIou,
    sahi,
    setSahi,
    imageSize,
    setImageSize,
    previews,
    setCapture,
    loadSamples,
    results,
    errors,
    uploadedCount,
    analyzing,
    runAnalysis,
    reportOpen,
    setReportOpen,
    generateReport,
    metrics,
  } = useDemo();
  const { zones, labels } = useZones();
  const [zonesOpen, setZonesOpen] = useState(false);
  const [loadingSamples, setLoadingSamples] = useState(false);
  const insights = computeInsights(DEMO_SLOTS, zones, results);
  const actions = recommend(insights);
  const analyzed = Object.keys(results).length > 0;
  const lastResult = Object.values(results)[0];
  const confidenceValue = Number.isFinite(confidence) ? confidence : 0.19;
  const iouValue = Number.isFinite(iou) ? iou : 0.7;

  const handleLoadSamples = async () => {
    setLoadingSamples(true);
    try {
      await loadSamples();
      toast.success("6 sample images loaded (08:00 – 18:00)");
    } catch {
      toast.error("Could not load the sample images");
    } finally {
      setLoadingSamples(false);
    }
  };

  return (
    <div lang="en">
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3 pb-6">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">Shelf availability</h1>
            <Badge variant="outline" className="border-primary/30 bg-primary/10 font-medium text-primary">
              DEMO · Sample times
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Segment tracking · demonstration scenario
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 text-sm text-muted-foreground">
            <Calendar className="size-3.5" />
            Today
          </span>
          <DemoBackendSelector value={provider} onChange={setProvider} disabled={analyzing || settingsBusy} />
          <Button variant="outline" size="sm" onClick={() => setZonesOpen(true)}>
            <SquareDashed className="size-4" />
            Segments
          </Button>
          <Button variant="outline" size="sm" onClick={handleLoadSamples} disabled={loadingSamples}>
            <Images className="size-4" />
            {loadingSamples ? "Loading…" : "Load demo images"}
          </Button>
          <Button variant="outline" size="sm" onClick={runAnalysis} disabled={analyzing || settingsBusy || !uploadedCount}>
            <Zap className="size-4" />
            {analyzing ? "Analyzing…" : "Analyze images"}
          </Button>
          <Button size="sm" onClick={generateReport}>
            <Download className="size-4" />
            Export report
          </Button>
        </div>
      </div>

      <section className="space-y-6">
        <details className="rounded-xl border border-border bg-card px-4 py-3 shadow-sm">
          <summary className="cursor-pointer text-sm font-semibold">Analysis settings</summary>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <label className="grid gap-1 text-sm">
              <span>Minimum confidence: <strong>{confidenceValue.toFixed(2)}</strong></span>
              <input type="range" min="0" max="1" step="0.01" value={confidenceValue} disabled={analyzing || settingsBusy} onChange={(e) => setConfidence(Number(e.target.value))} className="w-full accent-primary" />
              <span className="text-xs text-muted-foreground">Lower: more detections; higher: more selective.</span>
            </label>
            <label className="grid gap-1 text-sm">
              <span>NMS IoU: <strong>{iouValue.toFixed(2)}</strong></span>
              <input type="range" min="0" max="1" step="0.01" value={iouValue} disabled={analyzing || settingsBusy || provider === "runpod"} onChange={(e) => setIou(Number(e.target.value))} className="w-full accent-primary" />
              <span className="text-xs text-muted-foreground">{provider === "runpod" ? "Available for the local model and AWS Lambda." : "Lower: removes more overlapping boxes."}</span>
            </label>
          </div>
          <label className="mt-4 grid max-w-xs gap-1 text-sm">
            <span>Processing size</span>
            <select value={imageSize} onChange={(e) => setImageSize(Number(e.target.value))} disabled={analyzing || settingsBusy || provider === "runpod"} className="h-9 rounded-md border border-input bg-background px-2 text-sm disabled:opacity-50">
              {[...new Set([640, 960, 1280, 1600, 1920, imageSize])].sort((a, b) => a - b).map((size) => <option key={size} value={size}>{size} px{size === 640 ? " (default)" : ""}</option>)}
            </select>
            <span className="text-xs text-muted-foreground">{provider === "runpod" ? "Available for the local model and AWS Lambda." : provider === "lambda" ? "Dynamic ONNX input. Larger sizes take longer." : "A larger size can take longer and use more memory."}</span>
          </label>
          <label className="mt-4 flex items-center gap-3 text-sm">
            <Switch checked={provider === "local" && sahi} onCheckedChange={setSahi} disabled={analyzing || settingsBusy || provider !== "local"} />
            <span><strong>SAHI</strong><span className="ml-2 text-xs text-muted-foreground">{provider === "local" ? "Analyzes image slices and the full image; takes longer." : "Available only for the local model."}</span></span>
          </label>
          <p className="mt-3 text-xs text-muted-foreground">Changes apply when you analyze the images again.</p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button type="button" size="sm" variant="outline" onClick={saveSettings} disabled={analyzing || settingsBusy}>{settingsBusy ? "Loading / saving…" : "Save settings"}</Button>
            <p className="text-xs text-muted-foreground">{settingsMessage} Use Save settings to persist your changes.</p>
          </div>
        </details>
        <DemoMetrics metrics={metrics} />

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Images by time</h2>
            <span className="text-xs text-muted-foreground">
              {DEMO_SLOTS.length} images · 08:00 – 18:00
              {Object.keys(errors).length > 0 && ` · ${Object.keys(errors).length} with analysis errors`}
            </span>
          </div>
          {lastResult && (
            <p className="mb-3 text-xs text-muted-foreground">
              Last analysis · {lastResult.provider === "local" ? "Local model" : lastResult.provider === "lambda" ? "AWS Lambda" : "RunPod"} · confidence {lastResult.confidenceThreshold.toFixed(2)}
              {lastResult.iouThreshold !== null && ` · IoU ${lastResult.iouThreshold.toFixed(2)}`}
              {lastResult.imageSize !== null && ` · size ${lastResult.imageSize} px`}
              {lastResult.provider === "local" && ` · SAHI ${lastResult.sahi ? "on" : "off"}`}
            </p>
          )}
          <DemoTimeline slots={DEMO_SLOTS} previews={previews} results={results} errors={errors} zones={zones} onUpload={setCapture} />
          {analyzed && (
            <div className="mt-3 grid gap-2 border-t border-border pt-3 sm:grid-cols-3">
              <p className="text-xs text-muted-foreground sm:col-span-3">
                Analysis results · {insights.analyzedCount} images analyzed · {insights.totalObjects} products ·{" "}
                {insights.totalMissing} gaps
                {insights.firstEmptyTime && ` · first gap ${insights.firstEmptyTime}`}
                {insights.lastEmptyTime && ` · last ${insights.lastEmptyTime}`}
              </p>
              {insights.slots.map(({ slot, objects, missing, analyzed: done }) => (
                <div key={slot.id} className="flex items-center justify-between rounded-lg border border-border bg-background px-2.5 py-1.5">
                  <span className="tnum text-xs font-medium">{slot.time}</span>
                  <span className="tnum text-xs text-muted-foreground">{done ? `${objects} prod.` : "—"}</span>
                  <span
                    className={
                      missing
                        ? "tnum rounded-full bg-amber-100 px-1.5 text-xs font-semibold text-amber-700"
                        : "tnum text-xs text-muted-foreground"
                    }
                  >
                    {done ? `${missing} gaps` : "—"}
                  </span>
                </div>
              ))}
            </div>
          )}
          {zones.length > 0 && (
            <div className="mt-3 border-t border-border pt-3">
              <p className="mb-2 text-sm font-semibold">By segment (gap × zone)</p>
              <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {insights.zones.map((z) => {
                  const times = z.slotsWithEmpty
                    .map((id) => DEMO_SLOTS.find((s) => s.id === id)?.time)
                    .filter(Boolean)
                    .join(", ");
                  const empty = z.empty > 0;
                  return (
                    <li
                      key={z.zone.id}
                      className={
                        empty
                          ? "flex items-center justify-between gap-2 rounded-lg border border-destructive/40 bg-destructive/5 p-2.5"
                          : "flex items-center justify-between gap-2 rounded-lg border border-border bg-background p-2.5"
                      }
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{z.zone.name}</p>
                        <p className="truncate text-xs text-muted-foreground">
                          {z.objects} products
                          {analyzed && times ? ` · gap at ${times}` : ""}
                        </p>
                      </div>
                      <span
                        className={
                          empty
                            ? "shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700"
                            : "shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary"
                        }
                      >
                        {z.empty} gaps
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold">Suggested actions (analysis rules)</h2>
          {actions.length ? (
            <ul className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-2">
              {actions.map((action) => (
                <li key={action.id} className="flex items-start gap-2">
                  <Play className={cn("mt-0.5 size-4 shrink-0", TONE[action.tone])} />
                  <span className={action.tone === "critical" ? "text-foreground" : undefined}>{action.text}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              Run the analysis to generate recommendations from the results.
            </p>
          )}
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-x-8 gap-y-4">
            <div className="flex items-center gap-2">
              <FileText className="size-5 text-primary" />
              <span className="text-sm font-semibold">Report summary</span>
            </div>
            <div className="hidden h-9 w-px bg-border sm:block" />
            <SummaryItem label="Images by time" value={`${metrics.captures} images (${metrics.observedHours})`} />
            <SummaryItem
              label="Segment with gaps"
              value={
                insights.zones.find((z) => z.empty)?.zone.name ??
                (zones.length ? (analyzed ? "no gaps detected" : "analysis pending") : "define segments")
              }
            />
            <SummaryItem
              label="Suggested action:"
              value={
                actions.find((a) => a.tone === "critical")?.text ??
                actions[0]?.text ??
                "analysis pending"
              }
              tone="primary"
            />
            <div className="ml-auto flex flex-col gap-1.5 text-xs text-muted-foreground">
              <span className="flex items-center gap-2">
                <span className="inline-block h-3.5 w-6 rounded border-2 border-dashed border-primary" aria-hidden />
                Segment without gaps
              </span>
              <span className="flex items-center gap-2">
                <span className="inline-block h-3.5 w-6 rounded border-2 border-dashed border-destructive" aria-hidden />
                Segment with gaps
              </span>
              <span className="flex items-center gap-2">
                <span className="inline-block h-3.5 w-6 rounded border-2 border-dashed border-amber-500" aria-hidden />
                Empty space (gap)
              </span>
            </div>
          </div>
          <p className="mt-3 border-t border-border pt-2 text-right text-[11px] text-muted-foreground">
            Sample times · Results depend on the images and inference.
          </p>
        </div>
      </section>

      <ZoneEditor
        open={zonesOpen}
        onOpenChange={setZonesOpen}
        reference={previews[DEMO_SLOTS[0].id]}
      />

      <DemoReportDialog
        open={reportOpen}
        onOpenChange={setReportOpen}
        slots={DEMO_SLOTS}
        metrics={metrics}
        results={results}
        errors={errors}
        zones={zones}
        labels={labels}
      />
    </div>
  );
}
