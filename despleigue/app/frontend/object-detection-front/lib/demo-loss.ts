import { missingInZone } from "@/lib/zones";
import type { CaptureSlot, DemoAnalysisResult } from "@/services/demo.service";
import type { Zone, ZoneLabel } from "@/stores/zones-store";

/** Assign a detection only when it matches a single selected label. */
export function labelGapCounts(slots: CaptureSlot[], results: Record<string, DemoAnalysisResult>, zones: Zone[], labels: ZoneLabel[]) {
  const bySlot = labelGapCountsBySlot(slots, results, zones, labels);
  const counts = Object.fromEntries(labels.map((label) => [label.id, 0]));
  let ambiguous = 0;
  for (const slot of slots) {
    const row = bySlot[slot.id];
    if (!row) continue;
    for (const label of labels) counts[label.id] += row.counts[label.id] ?? 0;
    ambiguous += row.ambiguous;
  }
  return { counts, ambiguous };
}

/** Counts unambiguous label gaps per analyzed capture for the report timeline. */
export function labelGapCountsBySlot(slots: CaptureSlot[], results: Record<string, DemoAnalysisResult>, zones: Zone[], labels: ZoneLabel[]) {
  const selectedIds = new Set(labels.map((label) => label.id));
  return Object.fromEntries(slots.map((slot) => {
    const result = results[slot.id];
    const counts = Object.fromEntries(labels.map((label) => [label.id, 0]));
    let ambiguous = 0;
    if (result) {
      for (const box of result.missing) {
        const matching = new Set(zones.filter((zone) =>
          missingInZone(box, result.width, result.height, zone, result.objects)).map((zone) => zone.labelId));
        if (matching.size === 1) {
          const id = [...matching][0];
          if (selectedIds.has(id)) counts[id] += 1;
        } else if (matching.size > 1 && [...matching].some((id) => selectedIds.has(id))) ambiguous += 1;
      }
    }
    return [slot.id, result ? { counts, ambiguous } : null];
  }));
}

export function lossEstimate(gaps: number, unitsPerGap: string, unitPrice: string, margin: string) {
  if (!unitsPerGap.trim() || !unitPrice.trim()) return null;
  const units = Number(unitsPerGap);
  const price = Number(unitPrice);
  const marginPercent = margin.trim() ? Number(margin) : null;
  if (!Number.isFinite(units) || units < 0 || !Number.isFinite(price) || price < 0 ||
      (marginPercent !== null && (!Number.isFinite(marginPercent) || marginPercent < 0 || marginPercent > 100))) return null;
  const lostUnits = gaps * units;
  const revenue = lostUnits * price;
  if (!Number.isFinite(lostUnits) || !Number.isFinite(revenue)) return null;
  return { lostUnits, revenue, contribution: marginPercent === null ? null : revenue * (marginPercent / 100) };
}
