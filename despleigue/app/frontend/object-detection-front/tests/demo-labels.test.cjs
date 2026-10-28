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

const legacy = { zones: [
  { id: "a", name: "Bonafont 600", x: 0, y: 0, w: 0.5, h: 1 },
  { id: "b", name: "Bonafont 600", x: 0.5, y: 0, w: 0.5, h: 1 },
  { id: "c", name: "Bonafont 1000", x: 0, y: 0, w: 0.5, h: 1 },
] };
let stored = JSON.stringify({ state: legacy, version: 0 });
globalThis.localStorage = {
  getItem: () => stored,
  setItem: (_key, value) => { stored = value; },
  removeItem: () => { stored = null; },
};
globalThis.window = { localStorage: globalThis.localStorage };
const { migrateZones, useZones } = load("stores/zones-store.ts");
useZones.persist.rehydrate();
assert.equal(useZones.getState().zones.length, 3);
assert.equal(useZones.getState().labels.length, 2);
assert.equal(JSON.parse(stored).version, 1);
const migrated = migrateZones(legacy);
assert.equal(migrated.zones.length, 3);
assert.equal(migrated.labels.length, 2);
assert.equal(migrated.zones[0].labelId, migrated.zones[1].labelId);
assert.deepEqual(migrated.zones.map(({ id, x, y, w, h }) => ({ id, x, y, w, h })), legacy.zones.map(({ id, x, y, w, h }) => ({ id, x, y, w, h })));
useZones.setState(migrated);
const firstLabel = migrated.labels[0].id;
useZones.getState().updateLabel(firstLabel, { name: "Agua 600", unitPrice: "18", margin: "30" });
assert.deepEqual(useZones.getState().zones.slice(0, 2).map((z) => z.name), ["Agua 600", "Agua 600"]);
assert.equal(useZones.getState().labels[0].unitPrice, "18");
useZones.getState().assignLabel("c", firstLabel);
assert.equal(useZones.getState().zones[2].labelId, firstLabel);
assert.equal(useZones.getState().zones[2].name, "Agua 600");

const geometry = load("lib/zones.ts");
const { labelGapCounts, lossEstimate } = load("lib/demo-loss.ts", (id) => id === "@/lib/zones" ? geometry : require(id));
const gap = { box: [0, 0, 100, 100], class: "missing" };
const results = { "14": { width: 100, height: 100, objects: [], missing: [gap] } };
const slots = [{ id: "14", time: "14:00" }];
let counts = labelGapCounts(slots, results, migrated.zones.slice(0, 2), migrated.labels);
assert.equal(counts.counts[firstLabel], 1, "one box over two segments with the same label is counted once");
assert.equal(counts.ambiguous, 0);
counts = labelGapCounts(slots, results, migrated.zones, migrated.labels.slice(0, 1));
assert.equal(counts.counts[firstLabel], 0, "one box spanning different labels must not be assigned arbitrarily");
assert.equal(counts.ambiguous, 1);
assert.deepEqual(lossEstimate(2, "3", "18", "30"), { lostUnits: 6, revenue: 108, contribution: 32.4 });
assert.equal(lossEstimate(2, "3", "", "30"), null);
assert.equal(lossEstimate(2, "3", "18", "101"), null);
console.log("Legacy migration, shared labels, deduplicated and ambiguous gaps, and per-label estimates passed");
