const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");

function load(path, resolve = require) {
  const source = fs.readFileSync(path, "utf8");
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  const exports = {};
  new Function("exports", "require", js)(exports, resolve);
  return exports;
}

const geometry = load("lib/zones.ts");
const resolve = (id) => id === "@/lib/zones" ? geometry : require(id);
const { computeInsights, recommend } = load("lib/insights.ts", resolve);
const { labelGapCounts } = load("lib/demo-loss.ts", resolve);
const zone = { id: "z", labelId: "label", name: "Bonafont", x: 0, y: 0, w: 1, h: 1 };
const box = (x1, y1, x2, y2) => ({ box: [x1, y1, x2, y2], class: "object" });
const fullGap = box(0, 0, 100, 100);
const check = (gap, objects) => geometry.missingInZone(gap, 100, 100, zone, objects);

assert.equal(check(fullGap, []), true);
assert.equal(check(box(0, 0, 60, 100), []), true);
assert.equal(check(box(0, 0, 59, 100), []), false);
assert.equal(check(fullGap, [box(0, 0, 41, 100)]), false);
assert.equal(check(fullGap, [box(0, 0, 40, 100)]), true);
assert.equal(check(fullGap, [box(0, 0, 30, 100), box(20, 0, 40, 100)]), true, "overlapping products must not be subtracted twice");
assert.equal(check(fullGap, [box(80, 0, 120, 100)]), true, "only overlap inside the segment counts");
assert.equal(check(fullGap, [box(0, 0, 20, 50), box(0, 50, 20, 100)]), true, "stacked products are counted once per pixel");
assert.equal(check({ ...fullGap, confidence: 0.9 }, [{ ...fullGap, confidence: 0.5 }]), true, "stronger matching gap wins over a conflicting product");
assert.equal(check({ ...fullGap, confidence: 0.5 }, [{ ...fullGap, confidence: 0.9 }]), false, "stronger matching product remains occupied");

const bottle = box(0, 0, 80, 100);
const result = { width: 100, height: 100, objects: [bottle], missing: [fullGap] };
const results = { "16": result };
assert.equal(geometry.zoneStats([zone], results)[0].empty, 0);
assert.equal(computeInsights([{ id: "16", time: "16:00" }], [zone], results).zones[0].empty, 0);
assert.equal(labelGapCounts([{ id: "16", time: "16:00" }], results, [zone], [{ id: "label" }]).counts.label, 0);
const duplicateZones = [zone, { ...zone, id: "other" }];
const duplicateResults = { "16": { ...result, objects: [], missing: [fullGap, fullGap], nMissing: 2, nObjects: 0 } };
const recommendations = recommend(computeInsights([{ id: "16", time: "16:00" }], duplicateZones, duplicateResults));
assert.equal(recommendations[0].text, recommendations[1].text);
assert.notEqual(recommendations[0].id, recommendations[1].id);
assert.match(recommendations[0].text, /2 gap detections/);
console.log("Segment overlap, occupied area, union of products, reporting and loss counts passed");
