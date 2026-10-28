import type { CaptureSlot, DemoAnalysisResult, DemoBox } from "@/services/demo.service";
import { center, inZone, missingInZone } from "@/lib/zones";
import type { Zone } from "@/stores/zones-store";

/**
 * Demo heuristic: based on inference results and the
 * drawn segments, derive period facts and
 * recommendations using deterministic rules. No canned text or AI:
 * every statement comes from a measured number.
 */

export interface SlotFacts {
  slot: CaptureSlot;
  objects: number;
  missing: number;
  analyzed: boolean;
}

export interface ZoneFacts {
  zone: Zone;
  /** Captures analyzed within the segment (with at least one product). */
  slotsWithProduct: string[];
  /** Captures analyzed where the segment had at least one gap. */
  slotsWithEmpty: string[];
  objects: number;
  empty: number;
  emptyBySlot: Record<string, number>;
}

export interface DemoInsights {
  slots: SlotFacts[];
  zones: ZoneFacts[];
  analyzedCount: number;
  firstEmptyTime: string | null;
  lastEmptyTime: string | null;
  /** Product decrease between the first and last analyzed capture. */
  productDrop: number | null;
  totalMissing: number;
  totalObjects: number;
}

function slotFacts(slots: CaptureSlot[], results: Record<string, DemoAnalysisResult>): SlotFacts[] {
  return slots.map((slot) => {
    const r = results[slot.id];
    return {
      slot,
      objects: r?.nObjects ?? 0,
      missing: r?.nMissing ?? 0,
      analyzed: !!r,
    };
  });
}

function zoneFacts(zones: Zone[], results: Record<string, DemoAnalysisResult>): ZoneFacts[] {
  return zones.map((zone) => {
    const facts: ZoneFacts = { zone, slotsWithProduct: [], slotsWithEmpty: [], objects: 0, empty: 0, emptyBySlot: {} };
    for (const [slotId, r] of Object.entries(results)) {
      if (!r.width || !r.height) continue;
      const inZ = (b: DemoBox) => inZone(center(b, r.width, r.height), zone);
      const objects = r.objects.filter(inZ).length;
      const empty = r.missing.filter((b) => missingInZone(b, r.width, r.height, zone, r.objects)).length;
      facts.emptyBySlot[slotId] = empty;
      facts.objects += objects;
      facts.empty += empty;
      if (objects) facts.slotsWithProduct.push(slotId);
      if (empty) facts.slotsWithEmpty.push(slotId);
    }
    return facts;
  });
}

export function computeInsights(
  slots: CaptureSlot[],
  zones: Zone[],
  results: Record<string, DemoAnalysisResult>,
): DemoInsights {
  const sf = slotFacts(slots, results);
  const analyzed = sf.filter((s) => s.analyzed);
  const emptySlots = analyzed.filter((s) => s.missing > 0);
  const first = analyzed[0];
  const last = analyzed[analyzed.length - 1];
  return {
    slots: sf,
    zones: zoneFacts(zones, results),
    analyzedCount: analyzed.length,
    firstEmptyTime: emptySlots[0]?.slot.time ?? null,
    lastEmptyTime: emptySlots.length ? emptySlots[emptySlots.length - 1].slot.time : null,
    productDrop: first && last && first.slot.id !== last.slot.id ? first.objects - last.objects : null,
    totalMissing: analyzed.reduce((sum, s) => sum + s.missing, 0),
    totalObjects: analyzed.reduce((sum, s) => sum + s.objects, 0),
  };
}

export interface DemoRecommendation {
  id: string;
  text: string;
  tone: "critical" | "warning" | "ok";
}

/**
 * Rules (in order of severity). Each recommendation cites the times/segments
 * derived from the data; no statement is hard-coded.
 */
export function recommend(insights: DemoInsights): DemoRecommendation[] {
  const out: DemoRecommendation[] = [];
  if (!insights.analyzedCount) return out;

  for (const z of insights.zones) {
    if (!z.empty) continue;
    const times = z.slotsWithEmpty
      .map((id) => insights.slots.find((s) => s.slot.id === id)?.slot.time)
      .filter(Boolean)
      .join(", ");
    out.push({
      id: `zone:${z.zone.id}`,
      tone: "critical",
      text: `Check “${z.zone.name}”: ${z.empty} gap detection${z.empty === 1 ? "" : "s"} across ${z.slotsWithEmpty.length} of ${insights.analyzedCount} analyzed images (${times}).`,
    });
  }

  if (insights.firstEmptyTime) {
    out.push({
      id: "period:first-last",
      tone: "warning",
      text: `First analyzed image with gaps: ${insights.firstEmptyTime}; last: ${insights.lastEmptyTime}.`,
    });
  }

  if (insights.productDrop !== null && insights.productDrop > 0) {
    out.push({
      id: "period:product-drop",
      tone: "warning",
      text: `${insights.productDrop} fewer products were detected in the last analyzed image than in the first.`,
    });
  }

  const cleanZones = insights.zones.filter((z) => !z.empty && z.objects > 0);
  if (cleanZones.length) {
    out.push({
      id: "zones:no-gaps",
      tone: "ok",
      text: `No gaps detected in ${cleanZones.map((z) => `“${z.zone.name}”`).join(", ")} across the analyzed images.`,
    });
  }

  if (!out.length) {
    out.push({ id: "period:no-gaps", tone: "ok", text: "No gaps detected in the analyzed images." });
  }
  return out;
}
