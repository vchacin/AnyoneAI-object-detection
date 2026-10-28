import type { DemoAnalysisResult, DemoBox } from "@/services/demo.service";
import type { Zone } from "@/stores/zones-store";

/** Centro de la caja normalizado a 0–1 según las dimensiones de la imagen. */
export function center(box: DemoBox, width: number, height: number) {
  return { x: (box.box[0] + box.box[2]) / 2 / width, y: (box.box[1] + box.box[3]) / 2 / height };
}

export function inZone(p: { x: number; y: number }, z: Zone) {
  return p.x >= z.x && p.x <= z.x + z.w && p.y >= z.y && p.y <= z.y + z.h;
}

export function resizedZone(zone: Zone, handle: string, point: { x: number; y: number }) {
  const minSize = 0.02;
  const left = handle.includes("w") ? Math.max(0, Math.min(point.x, zone.x + zone.w - minSize)) : zone.x;
  const right = handle.includes("e") ? Math.min(1, Math.max(point.x, zone.x + minSize)) : zone.x + zone.w;
  const top = handle.includes("n") ? Math.max(0, Math.min(point.y, zone.y + zone.h - minSize)) : zone.y;
  const bottom = handle.includes("s") ? Math.min(1, Math.max(point.y, zone.y + minSize)) : zone.y + zone.h;
  return { x: left, y: top, w: right - left, h: bottom - top };
}

/** Subtracts the area occupied by products from the gap before evaluating the segment. */
export function missingInZone(box: DemoBox, width: number, height: number, zone: Zone, objects: DemoBox[]) {
  if (width <= 0 || height <= 0 || zone.w <= 0 || zone.h <= 0) return false;
  const left = Math.max(box.box[0], zone.x * width);
  const top = Math.max(box.box[1], zone.y * height);
  const right = Math.min(box.box[2], (zone.x + zone.w) * width);
  const bottom = Math.min(box.box[3], (zone.y + zone.h) * height);
  if (right <= left || bottom <= top) return false;

  const occupied = objects.filter((object) => {
    if (object.confidence == null || box.confidence == null || object.confidence >= box.confidence) return true;
    const w = Math.max(0, Math.min(box.box[2], object.box[2]) - Math.max(box.box[0], object.box[0]));
    const h = Math.max(0, Math.min(box.box[3], object.box[3]) - Math.max(box.box[1], object.box[1]));
    const overlap = w * h;
    const gapArea = Math.max(0, box.box[2] - box.box[0]) * Math.max(0, box.box[3] - box.box[1]);
    const objectArea = Math.max(0, object.box[2] - object.box[0]) * Math.max(0, object.box[3] - object.box[1]);
    // Nearly identical boxes with higher gap confidence are conflicting detections.
    return overlap < 0.7 * (gapArea + objectArea - overlap);
  }).map((object) => ({
    left: Math.max(left, object.box[0]),
    top: Math.max(top, object.box[1]),
    right: Math.min(right, object.box[2]),
    bottom: Math.min(bottom, object.box[3]),
  })).filter((rect) => rect.right > rect.left && rect.bottom > rect.top);
  const edges = [...new Set(occupied.flatMap((rect) => [rect.left, rect.right]))].sort((a, b) => a - b);
  let occupiedArea = 0;
  for (let i = 1; i < edges.length; i += 1) {
    const x1 = edges[i - 1], x2 = edges[i];
    const spans = occupied.filter((rect) => rect.left < x2 && rect.right > x1)
      .map((rect) => [rect.top, rect.bottom] as const).sort((a, b) => a[0] - b[0]);
    let coveredHeight = 0, end = top;
    for (const [y1, y2] of spans) {
      coveredHeight += Math.max(0, y2 - Math.max(y1, end));
      end = Math.max(end, y2);
    }
    occupiedArea += (x2 - x1) * coveredHeight;
  }
  const uncoveredArea = (right - left) * (bottom - top) - occupiedArea;
  return uncoveredArea >= 0.6 * zone.w * width * zone.h * height;
}

export interface ZoneStat {
  zone: Zone;
  /** Products detected within the segment (all captures). */
  objects: number;
  /** Empty spaces detected within the segment (all captures). */
  empty: number;
  /** IDs of time slots where at least one empty space was detected in the segment. */
  slotIds: string[];
}

/** Cruce de resultados de analysis × segmentos dibujados. */
export function zoneStats(zones: Zone[], results: Record<string, DemoAnalysisResult>): ZoneStat[] {
  return zones.map((zone) => {
    const stat: ZoneStat = { zone, objects: 0, empty: 0, slotIds: [] };
    for (const [slotId, r] of Object.entries(results)) {
      if (!r.width || !r.height) continue;
      const empty = r.missing.filter((b) => missingInZone(b, r.width, r.height, zone, r.objects)).length;
      stat.empty += empty;
      stat.objects += r.objects.filter((b) => inZone(center(b, r.width, r.height), zone)).length;
      if (empty) stat.slotIds.push(slotId);
    }
    return stat;
  });
}
