"use client";

import { useState } from "react";
import { Download, Printer, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { CaptureSlot, DemoAnalysisResult } from "@/services/demo.service";
import type { DemoMetrics } from "@/hooks/use-demo";
import { computeInsights, recommend } from "@/lib/insights";
import { labelGapCounts, labelGapCountsBySlot, lossEstimate } from "@/lib/demo-loss";
import type { Zone, ZoneLabel } from "@/stores/zones-store";

interface DemoReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  slots: CaptureSlot[];
  metrics: DemoMetrics;
  results?: Record<string, DemoAnalysisResult>;
  errors?: Record<string, string>;
  zones?: Zone[];
  labels?: ZoneLabel[];
}

export function DemoReportDialog({ open, onOpenChange, slots, metrics, results = {}, errors = {}, zones = [], labels = [] }: DemoReportDialogProps) {
  const [chosenLabels, setChosenLabels] = useState<string[] | null>(null);
  const [unitsPerGap, setUnitsPerGap] = useState("");
  const insights = computeInsights(slots, zones, results);
  const recommendations = recommend(insights);
  const capturesWithGaps = insights.slots.filter((slot) => slot.analyzed && slot.missing > 0).length;
  const usedLabels = labels.filter((label) => zones.some((zone) => zone.labelId === label.id));
  const selectedIds = chosenLabels ?? usedLabels.filter((label) => /bonafont/i.test(label.name)).map((label) => label.id);
  const selectedLabels = usedLabels.filter((label) => selectedIds.includes(label.id));
  const gapCounts = labelGapCounts(slots, results, zones, selectedLabels);
  const gapCountsBySlot = labelGapCountsBySlot(slots, results, zones, selectedLabels);
  const impacts = selectedLabels.map((label) => ({
    label,
    gaps: gapCounts.counts[label.id],
    estimate: insights.analyzedCount ? lossEstimate(gapCounts.counts[label.id], unitsPerGap, label.unitPrice, label.margin) : null,
  }));
  const estimated = impacts.filter((item) => item.estimate !== null);
  const totalRevenue = estimated.reduce((sum, item) => sum + item.estimate!.revenue, 0);
  const projections = [
    { key: "week", title: "Weekly", multiplier: 7, basis: "7 × this demo day" },
    { key: "month", title: "Monthly", multiplier: 365 / 12, basis: "30.4 × this demo day" },
    { key: "year", title: "Yearly", multiplier: 365, basis: "365 × this demo day" },
  ];
  const currency = (value: number) => value.toLocaleString("en-US", { style: "currency", currency: "MXN" });
  const number = (value: number) => value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  const opportunityBySlot = slots.map((slot) => {
    const row = gapCountsBySlot[slot.id];
    if (!row) return null;
    let total = 0;
    let pricedLabels = 0;
    for (const label of selectedLabels) {
      const estimate = lossEstimate(row.counts[label.id] ?? 0, unitsPerGap, label.unitPrice, "");
      if (estimate) {
        total += estimate.revenue;
        pricedLabels += 1;
      }
    }
    return pricedLabels ? total : null;
  });
  const observedGapsBySlot = slots.map((slot) => {
    const row = gapCountsBySlot[slot.id];
    return row ? Object.values(row.counts).reduce((sum, count) => sum + count, 0) : null;
  });
  const reportHtml = () => document.getElementById("demo-report-content")?.outerHTML ?? "";
  const documentHtml = () => `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>ShelfVision Report</title></head><body style="font-family:Arial,sans-serif;padding:24px;max-width:760px;margin:auto;color:#222">${reportHtml()}</body></html>`;

  const handlePrint = () => {
    const w = window.open("", "_blank");
    if (!w) return;
    w.document.write(documentHtml());
    w.document.close();
    w.print();
  };

  const handleDownload = () => {
    const url = URL.createObjectURL(new Blob([documentHtml()], { type: "text/html" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "shelfvision-report.html";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent lang="en" className="max-h-[95vh] w-[calc(100%-2rem)] sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Availability report</DialogTitle>
          <DialogDescription>Results for the analyzed images and defined segments.</DialogDescription>
        </DialogHeader>

        <div className="min-h-0 min-w-0 max-h-[65vh] overflow-y-auto overflow-x-hidden rounded-lg border bg-slate-100 p-3 text-neutral-900 sm:p-6">
          <div className="mb-4 rounded-lg border border-slate-200 bg-white p-4 text-sm">
            <h3 className="font-semibold text-slate-900">Loss assumptions · OXXO / Bonafont</h3>
            <p className="mt-1 text-xs text-slate-600">Select labels. Set their prices and margins in Segments.</p>
            <fieldset className="mt-3">
              <legend className="text-xs font-medium text-slate-700">Labels</legend>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
                {usedLabels.length ? usedLabels.map((label) => (
                  <label key={label.id} className="flex items-center gap-2 text-xs text-slate-700">
                    <input type="checkbox" checked={selectedIds.includes(label.id)} onChange={(e) => setChosenLabels(e.target.checked ? [...selectedIds, label.id] : selectedIds.filter((id) => id !== label.id))} />
                    {label.name}
                  </label>
                )) : <span className="text-xs text-slate-500">Define segments to calculate the impact.</span>}
              </div>
            </fieldset>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="grid gap-1 text-xs font-medium text-slate-700">Unsold units per gap and image
                <input type="number" min="0" step="any" inputMode="decimal" value={unitsPerGap} onChange={(e) => setUnitsPerGap(e.target.value)} placeholder="e.g. 2" className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-900" />
              </label>
            </div>
            <p className="mt-2 text-xs text-slate-500">The assumption per image must account for the time period it represents; the model does not determine it.</p>
          </div>
          <div id="demo-report-content" style={{ background: "#fff", color: "#1e293b", padding: "20px", overflowWrap: "anywhere", lineHeight: 1.5, fontFamily: "Arial, sans-serif" }}>
            <div style={{ borderBottom: "2px solid #f97316", paddingBottom: "14px", marginBottom: "20px" }}>
              <p style={{ margin: "0 0 4px", fontSize: "11px", fontWeight: 700, letterSpacing: "0.12em", color: "#c2410c" }}>SHELFVISION · DEMO</p>
              <h1 style={{ fontSize: "22px", lineHeight: 1.25, margin: "0 0 6px", color: "#0f172a" }}>Shelf availability report</h1>
              <p style={{ margin: 0, fontSize: "13px", color: "#64748b" }}>{metrics.captures} of {slots.length} images analyzed · Times: {metrics.observedHours}</p>
            </div>

            <div role="note" aria-label="Important sales estimate limitation" style={{ border: "2px solid #b45309", borderLeft: "8px solid #c2410c", borderRadius: "8px", background: "#fff7ed", padding: "14px 16px", margin: "0 0 20px", color: "#7c2d12" }}>
              <p style={{ margin: "0 0 5px", fontSize: "14px", fontWeight: 800, letterSpacing: "0.02em" }}>IMPORTANT: THIS IS NOT ACTUAL SALES DATA</p>
              <p style={{ margin: 0, fontSize: "12px" }}>Images only show visible shelf conditions. They cannot tell how many units sold, confirm inventory in the backroom, or prove that a detected gap caused a lost sale. The opportunity estimate below uses only the units-per-gap assumption entered here and prices saved for each label. No OXXO / Bonafont point-of-sale data is connected.</p>
              <p style={{ margin: "8px 0 0", fontSize: "12px", fontWeight: 700 }}>Reference scenario: approximately 64 water packages per store per day</p>
              <p style={{ margin: "4px 0 0", fontSize: "12px" }}>13 million daily transactions in OXXO Mexico in 2025 (<a href="https://informeanual.femsa.com/operating-performance.html">FEMSA</a>) ÷ 24,297 stores at year-end (<a href="https://www.milenio.com/negocios/femsa-reporta-ingresos-840-mil-millones-pesos">Milenio</a>) ≈ 535 transactions per store per day. Assuming 10% include bottled water and 1.2 packages per water transaction: 535 × 10% × 1.2 ≈ 64 packages per day. A multipack counts as one package. The denominator is a year-end store count, so this is an approximation, not the actual average traffic per store.</p>
              <p style={{ margin: "6px 0 0", fontSize: "12px" }}>The 10% and 1.2 figures are illustrative assumptions, not reported measurements. At 7%–13% incidence with 1.2 packages, the scenario is approximately 45–83 packages daily. <a href="https://www.kantar.com/latin-america/Inspiracion/Consumo-Masivo/Consumo-agua-embotellada">Kantar’s 2017 study</a> provides category context, including consumption outside the home, but does not validate these assumptions. The national OXXO benchmark does not establish sales for a specific store, Bonafont, a specific presentation, or a shelf gap. Validate with store-level transaction data.</p>
              <p style={{ margin: "6px 0 0", fontSize: "12px" }}>The 64-package scenario is context only: it is not used in the report calculation. Estimated opportunity uses the manually entered units per gap and image and label prices. Prices, product mix, margins, and the relationship between gaps and missed sales require separate validation. Sales are revenue, not cost or profit.</p>
            </div>

            <h2 style={{ fontSize: "16px", margin: "0 0 8px", color: "#0f172a" }}>Executive summary</h2>
            {insights.analyzedCount ? (
              <p style={{ margin: "0 0 16px", fontSize: "13px" }}>
                Gaps were detected in {capturesWithGaps} of {insights.analyzedCount} analyzed images.
                {insights.firstEmptyTime && ` First image with gaps: ${insights.firstEmptyTime}; last: ${insights.lastEmptyTime}.`}
              </p>
            ) : <p style={{ fontSize: "13px" }}>No images have been analyzed yet.</p>}

            <table style={{ width: "100%", tableLayout: "fixed", borderCollapse: "collapse", marginBottom: "24px", fontSize: "13px" }}>
              <tbody>
                {[
                  ["Images with gaps", insights.analyzedCount ? `${capturesWithGaps} of ${insights.analyzedCount}` : "—"],
                  ["Products detected across images", insights.analyzedCount ? insights.totalObjects : "—"],
                  ["Gaps detected across images", insights.analyzedCount ? insights.totalMissing : "—"],
                ].map(([label, value]) => (
                  <tr key={label}>
                    <th scope="row" style={{ width: "70%", borderBottom: "1px solid #e2e8f0", padding: "8px 10px", textAlign: "left", fontWeight: 400, background: "#f8fafc" }}>{label}</th>
                    <td style={{ borderBottom: "1px solid #e2e8f0", padding: "8px 10px", textAlign: "right", fontWeight: 700, color: "#0f172a" }}>{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <h2 style={{ fontSize: "16px", margin: "0 0 8px", color: "#0f172a" }}>Estimated impact · Bonafont</h2>
            {selectedLabels.length && insights.analyzedCount ? (
              <>
                <p style={{ margin: "0 0 10px", fontSize: "12px", color: "#475569" }}>OXXO demo scenario · Price and margin by label</p>
                <table style={{ width: "100%", tableLayout: "fixed", borderCollapse: "collapse", marginBottom: "8px", fontSize: "12px" }}>
                  <thead><tr style={{ background: "#eef2f6", color: "#475569" }}>
                    <th scope="col" style={{ width: "37%", padding: "8px 5px", textAlign: "left" }}>Label</th>
                    <th scope="col" style={{ width: "15%", padding: "8px 5px", textAlign: "center" }}>Gaps</th>
                    <th scope="col" style={{ width: "24%", padding: "8px 5px", textAlign: "right" }}>Estimated sales</th>
                    <th scope="col" style={{ width: "24%", padding: "8px 5px", textAlign: "right" }}>Estimated margin</th>
                  </tr></thead>
                  <tbody>{impacts.map(({ label, gaps, estimate }) => (
                    <tr key={label.id} style={{ borderBottom: "1px solid #e2e8f0", verticalAlign: "top" }}>
                      <th scope="row" style={{ padding: "8px 5px", textAlign: "left", fontWeight: 500 }}>{label.name}</th>
                      <td style={{ padding: "8px 5px", textAlign: "center" }}>{number(gaps)}</td>
                      <td style={{ padding: "8px 5px", textAlign: "right", color: "#c2410c" }}>{estimate ? currency(estimate.revenue) : "Pending"}</td>
                      <td style={{ padding: "8px 5px", textAlign: "right" }}>{estimate?.contribution != null ? currency(estimate.contribution) : "—"}</td>
                    </tr>
                  ))}</tbody>
                </table>
                {estimated.length > 0 && <p style={{ margin: "8px 0", fontSize: "13px", fontWeight: 700 }}>Estimated lost sales{estimated.length < impacts.length ? " (subtotal for priced labels)" : ""}: {currency(totalRevenue)}</p>}
                <p style={{ margin: "0 0 24px", fontSize: "11px", color: "#64748b" }}>
                  {unitsPerGap.trim() && `Assumption: ${unitsPerGap} unsold units per gap and image. `}
                  {estimated.length > 0 && `Prices and margins: ${estimated.map(({ label }) => `${label.name}: ${currency(Number(label.unitPrice))}${label.margin.trim() ? `, margin ${number(Number(label.margin))} %` : ", margin not specified"}`).join("; ")}. `}
                  Calculation: gaps × units per gap and image × label price; margin is a percentage of sales. A gap covering several segments with the same label is counted once.
                  {impacts.some((item) => !item.estimate) && " Labels without a valid price or assumption are pending and excluded from the subtotal."}
                  {gapCounts.ambiguous > 0 && ` ${gapCounts.ambiguous} detections spanning different labels were excluded because the gap cannot be attributed to a single product.`}
                  {" "}The same gap may be counted in multiple images; set the per-image assumption to avoid counting the same period twice.
                  This is an estimate, not a confirmed sale or loss.
                  {insights.analyzedCount < slots.length && " Only analyzed images are included."}
                </p>
              </>
            ) : <p style={{ margin: "0 0 24px", fontSize: "12px", color: "#64748b" }}>Select labels, analyze images, and set their prices in Segments to calculate an estimate.</p>}

            <h2 style={{ fontSize: "16px", margin: "0 0 4px", color: "#0f172a" }}>Gap observations and estimated opportunity over time</h2>
            <p style={{ margin: "0 0 8px", fontSize: "11px", color: "#64748b" }}>Orange bars: unambiguous gap detections in each analyzed image. Blue line: estimated sales opportunity for those gaps in that image, not actual or cumulative sales.</p>
            <ReportTimelineChart slots={slots} gaps={observedGapsBySlot} opportunity={opportunityBySlot} />
            <p style={{ margin: "0 0 24px", fontSize: "11px", color: "#7c2d12" }}>The opportunity line is gaps × the manually entered units-per-gap-and-image assumption × label price. It is a scenario estimate per capture. It does not interpolate sales between captures, measure sell-through, or establish a causal loss. Captures without results are left blank.</p>

            <h2 style={{ fontSize: "16px", margin: "0 0 4px", color: "#0f172a" }}>Estimated missed-sales opportunity · projections</h2>
            <div role="note" aria-label="Projection assumptions" style={{ border: "2px solid #b45309", borderRadius: "8px", background: "#fff7ed", padding: "12px 14px", margin: "0 0 12px", color: "#7c2d12" }}>
              <p style={{ margin: 0, fontSize: "12px", fontWeight: 800 }}>SCENARIO ONLY — the weekly, monthly, and yearly graphs repeat this one demo day at the same rate.</p>
              <p style={{ margin: "4px 0 0", fontSize: "11px" }}>The blue bar is potential revenue associated with detected gaps if those gaps had been replenished, using the entered units-per-gap assumption. It is not measured lost revenue. Actual sales under the observed conditions are unknown without OXXO POS data; they are not treated as zero.</p>
            </div>
            {insights.analyzedCount && estimated.length ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: "10px", marginBottom: "8px" }}>
                {projections.map((period) => (
                  <ProjectionGraph key={period.key} title={period.title} basis={period.basis} amount={totalRevenue * period.multiplier} maxAmount={totalRevenue * 365} currency={currency} />
                ))}
              </div>
            ) : <p style={{ margin: "0 0 8px", fontSize: "12px", color: "#64748b" }}>Enter units per gap and valid label prices to plot these scenarios.</p>}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "10px", margin: "12px 0" }}>
              <UnavailableTrend title="Observed variation by weekday" labels={["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]} />
              <UnavailableTrend title="Observed variation by month" labels={["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]} />
            </div>
            <p style={{ margin: "0 0 8px", fontSize: "11px", color: "#7c2d12" }}>Weekday and calendar-month variation cannot be calculated from these images: all six timestamps are from one undated demo day. That requires dated observations across multiple days/months or store-level POS history. The national INEGI category series is not applied as a store-level adjustment.</p>
            <p style={{ margin: "0 0 24px", fontSize: "10px", color: "#64748b" }}>Category reference: <a href="https://nube.agricultura.gob.mx/industriaAgroalimentaria/abril2026.php" style={{ color: "#1d4ed8", textDecoration: "underline" }}>DGSIAP / INEGI EMIM</a> reports monthly national water volume (purified and carbonated); it does not provide this retailer’s hourly or weekday sales.</p>

            <h2 style={{ fontSize: "16px", margin: "0 0 8px", color: "#0f172a" }}>Results by time</h2>
            <table style={{ width: "100%", tableLayout: "fixed", borderCollapse: "collapse", marginBottom: "24px", fontSize: "12px" }}>
              <thead>
                <tr style={{ background: "#eef2f6", color: "#475569" }}>
                  <th scope="col" style={{ width: "14%", padding: "8px 5px", textAlign: "left" }}>Time</th>
                  <th scope="col" style={{ width: "15%", padding: "8px 5px", textAlign: "center" }}>Products</th>
                  <th scope="col" style={{ width: "13%", padding: "8px 5px", textAlign: "center" }}>Gaps</th>
                  <th scope="col" style={{ width: "58%", padding: "8px 5px", textAlign: "left" }}>Segments with gaps</th>
                </tr>
              </thead>
              <tbody>
                {slots.map((slot) => {
                  const result = results[slot.id];
                  const affected = insights.zones.filter((z) => (z.emptyBySlot[slot.id] ?? 0) > 0);
                  return (
                    <tr key={slot.id} style={{ borderBottom: "1px solid #e2e8f0", verticalAlign: "top" }}>
                      <th scope="row" style={{ padding: "9px 5px", textAlign: "left", color: "#0f172a" }}>{slot.time}</th>
                      <td style={{ padding: "9px 5px", textAlign: "center" }}>{result ? result.nObjects : "—"}</td>
                      <td style={{ padding: "9px 5px", textAlign: "center", fontWeight: result?.nMissing ? 700 : 400, color: result?.nMissing ? "#c2410c" : "#475569" }}>{result ? result.nMissing : "—"}</td>
                      <td style={{ padding: "9px 5px" }}>
                        {!result ? (errors[slot.id] ? "Analysis error" : "Not analyzed") : !zones.length ? "No segments defined" : affected.length ? affected.map((z) => (
                          <div key={z.zone.id}>{z.zone.name}: <strong>{z.emptyBySlot[slot.id]}</strong></div>
                        )) : "No gaps detected"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {zones.length > 0 && (
              <>
                <h2 style={{ fontSize: "16px", margin: "0 0 8px", color: "#0f172a" }}>Summary by segment</h2>
                <table style={{ width: "100%", tableLayout: "fixed", borderCollapse: "collapse", marginBottom: "24px", fontSize: "12px" }}>
                  <thead><tr style={{ background: "#eef2f6", color: "#475569" }}>
                    <th scope="col" style={{ width: "40%", padding: "8px 5px", textAlign: "left" }}>Segment</th>
                    <th scope="col" style={{ width: "20%", padding: "8px 5px", textAlign: "center" }}>Gaps</th>
                    <th scope="col" style={{ width: "40%", padding: "8px 5px", textAlign: "left" }}>Times with gaps</th>
                  </tr></thead>
                  <tbody>{insights.zones.map((z) => (
                    <tr key={z.zone.id} style={{ borderBottom: "1px solid #e2e8f0", verticalAlign: "top" }}>
                      <th scope="row" style={{ padding: "9px 5px", textAlign: "left", fontWeight: 500 }}>{z.zone.name}</th>
                      <td style={{ padding: "9px 5px", textAlign: "center" }}>{insights.analyzedCount ? z.empty : "—"}</td>
                      <td style={{ padding: "9px 5px" }}>{z.slotsWithEmpty.map((id) => slots.find((s) => s.id === id)?.time).filter(Boolean).join(", ") || "—"}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </>
            )}

            {recommendations.length > 0 && (
              <>
                <h2 style={{ fontSize: "16px", margin: "0 0 8px", color: "#0f172a" }}>Observations and actions</h2>
                <ul style={{ margin: "0 0 20px", paddingLeft: "20px", fontSize: "13px" }}>
                  {recommendations.map((item) => <li key={item.id} style={{ marginBottom: "6px" }}>{item.text}</li>)}
                </ul>
              </>
            )}

            <p style={{ borderTop: "1px solid #e2e8f0", paddingTop: "12px", margin: "0", fontSize: "11px", color: "#64748b" }}>
              Times are labels for the demo scenario. Segments and their names are defined by the user.
              A gap is assigned to a segment if it covers at least 60% of its area after subtracting detected products.
              When a product and a gap have nearly identical boxes, the gap is favored if its confidence is higher; a gap can appear in multiple segments.
              Detections are visual estimates: an empty space does not indicate how many units are missing or confirm inventory.
              Totals add detections across images and do not represent unique products or gaps.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}><X /> Close</Button>
          <Button variant="outline" onClick={handleDownload}><Download /> Download HTML</Button>
          <Button onClick={handlePrint}><Printer /> Print / PDF</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ReportTimelineChart({ slots, gaps, opportunity }: {
  slots: CaptureSlot[];
  gaps: (number | null)[];
  opportunity: (number | null)[];
}) {
  const width = 760;
  const height = 270;
  const left = 54;
  const right = 78;
  const top = 42;
  const bottom = 48;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const count = Math.max(slots.length, 1);
  const x = (index: number) => left + (count === 1 ? plotWidth / 2 : (index / (count - 1)) * plotWidth);
  const maxGaps = Math.max(1, ...gaps.filter((value): value is number => value !== null));
  const validOpportunity = opportunity.filter((value): value is number => value !== null);
  const maxOpportunity = Math.max(1, ...validOpportunity);
  const yGaps = (value: number) => top + plotHeight - (value / maxGaps) * plotHeight;
  const yOpportunity = (value: number) => top + plotHeight - (value / maxOpportunity) * plotHeight;
  const opportunityPath = opportunity.reduce((path, value, index) => {
    if (value === null) return path;
    return `${path}${path && opportunity[index - 1] !== null ? " L" : " M"}${x(index)},${yOpportunity(value)}`;
  }, "");
  const barWidth = Math.min(40, plotWidth / count * 0.48);
  const formatMoney = (value: number) => `MX$${value.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;

  return (
    <svg role="img" aria-label="Timeline of observed gap detections and estimated opportunity per image" viewBox={`0 0 ${width} ${height}`} style={{ display: "block", width: "100%", height: "auto", background: "#fff", border: "1px solid #cbd5e1", borderRadius: "6px", marginBottom: "6px" }}>
      <text x={left} y="18" fontSize="10" fill="#9a3412">Gap detections</text>
      <rect x={left + 92} y="9" width="10" height="10" rx="2" fill="#f97316" />
      <text x={left + 107} y="18" fontSize="10" fill="#475569">Observed in image</text>
      <line x1={left + 230} y1="14" x2={left + 249} y2="14" stroke="#2563eb" strokeWidth="2.5" />
      <text x={left + 255} y="18" fontSize="10" fill="#475569">Est. opportunity / image</text>
      {[0, 0.5, 1].map((fraction) => {
        const y = top + plotHeight * (1 - fraction);
        return <g key={fraction}>
          <line x1={left} y1={y} x2={width - right} y2={y} stroke="#e2e8f0" strokeWidth="1" />
          <text x={left - 8} y={y + 3} textAnchor="end" fontSize="9" fill="#64748b">{numberAxis(maxGaps * fraction)}</text>
          {validOpportunity.length > 0 && <text x={width - right + 8} y={y + 3} fontSize="9" fill="#64748b">{formatMoney(maxOpportunity * fraction)}</text>}
        </g>;
      })}
      <line x1={left} y1={top} x2={left} y2={top + plotHeight} stroke="#94a3b8" />
      <line x1={width - right} y1={top} x2={width - right} y2={top + plotHeight} stroke="#94a3b8" />
      <text x="12" y={top + plotHeight / 2} transform={`rotate(-90 12 ${top + plotHeight / 2})`} textAnchor="middle" fontSize="9" fill="#475569">Detected gaps</text>
      {validOpportunity.length > 0 && <text x={width - 8} y={top + plotHeight / 2} transform={`rotate(90 ${width - 8} ${top + plotHeight / 2})`} textAnchor="middle" fontSize="9" fill="#475569">Opportunity (MXN)</text>}
      {slots.map((slot, index) => {
        const gapCount = gaps[index];
        const centerX = x(index);
        return <g key={slot.id}>
          {gapCount !== null && <rect x={centerX - barWidth / 2} y={yGaps(gapCount)} width={barWidth} height={Math.max(1, top + plotHeight - yGaps(gapCount))} rx="2" fill="#f97316" opacity="0.8" />}
          <text x={centerX} y={height - 25} textAnchor="middle" fontSize="10" fill="#334155">{slot.time}</text>
          {gapCount !== null && <text x={centerX} y={height - 10} textAnchor="middle" fontSize="8" fill="#64748b">{gapCount} gaps</text>}
        </g>;
      })}
      {validOpportunity.length > 0 && <path d={opportunityPath} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />}
      {slots.map((slot, index) => opportunity[index] !== null && <circle key={slot.id} cx={x(index)} cy={yOpportunity(opportunity[index]!)} r="3.5" fill="#2563eb" stroke="#fff" strokeWidth="1.5" />)}
      {validOpportunity.length === 0 && <text x={left + plotWidth / 2} y={top + plotHeight / 2} textAnchor="middle" fontSize="11" fill="#64748b">Enter units per gap and valid label prices to plot an estimate.</text>}
      <text x={left + plotWidth / 2} y={height - 1} textAnchor="middle" fontSize="10" fill="#334155">Capture time</text>
    </svg>
  );
}

function ProjectionGraph({ title, basis, amount, maxAmount, currency }: {
  title: string;
  basis: string;
  amount: number;
  maxAmount: number;
  currency: (value: number) => string;
}) {
  const width = 320;
  const height = 122;
  const barWidth = 280;
  const fillWidth = Math.max(amount > 0 ? 2 : 0, Math.min(barWidth, (amount / Math.max(maxAmount, 1)) * barWidth));
  return (
    <svg role="img" aria-label={`${title} projection of ${currency(amount)} potential opportunity if detected gaps were replenished; actual POS sales are unavailable`} viewBox={`0 0 ${width} ${height}`} style={{ display: "block", width: "100%", height: "auto", background: "#fff", border: "1px solid #cbd5e1", borderRadius: "6px" }}>
      <text x="14" y="20" fontSize="15" fontWeight="700" fill="#0f172a">{title}</text>
      <text x="14" y="36" fontSize="10" fill="#64748b">{basis}</text>
      <text x="14" y="58" fontSize="10" fill="#475569">Potential if gaps were replenished · estimated</text>
      <rect x="14" y="66" width={barWidth} height="14" rx="4" fill="#ffedd5" />
      {amount > 0 && <rect x="14" y="66" width={fillWidth} height="14" rx="4" fill="#f97316" />}
      <text x="14" y="98" fontSize="13" fontWeight="700" fill="#9a3412">{currency(amount)}</text>
      <text x="14" y="114" fontSize="9" fill="#64748b">Actual POS sales: not provided · not zero</text>
    </svg>
  );
}

function UnavailableTrend({ title, labels }: { title: string; labels: string[] }) {
  return (
    <div role="img" aria-label={`${title}: unavailable because the demo has no dated multi-day observations`} style={{ border: "1px solid #cbd5e1", borderRadius: "6px", background: "#fff", padding: "10px" }}>
      <p style={{ margin: "0 0 8px", fontSize: "12px", fontWeight: 700, color: "#334155" }}>{title}</p>
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${labels.length}, minmax(0, 1fr))`, gap: "3px", alignItems: "end" }}>
        {labels.map((label) => <div key={label} style={{ minWidth: 0, textAlign: "center" }}>
          <div style={{ height: "30px", display: "grid", placeItems: "center", borderBottom: "1px dashed #94a3b8", color: "#94a3b8", fontSize: "12px" }}>—</div>
          <span style={{ display: "block", marginTop: "4px", fontSize: labels.length > 7 ? "8px" : "9px", color: "#64748b" }}>{label}</span>
        </div>)}
      </div>
      <p style={{ margin: "8px 0 0", fontSize: "9px", color: "#7c2d12" }}>No dated history · dash means no data, not zero.</p>
    </div>
  );
}

function numberAxis(value: number) {
  return value.toLocaleString("en-US", { maximumFractionDigits: 1 });
}
