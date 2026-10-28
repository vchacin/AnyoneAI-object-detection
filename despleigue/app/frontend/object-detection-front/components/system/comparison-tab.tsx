"use client";

import { ChevronLeft, ChevronRight, GitCompareArrows } from "lucide-react";
import { Choice } from "@/components/common/choice";
import { QueryBoundary } from "@/components/common/query-boundary";
import { EmptyState, RowsSkeleton } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useComparisonReview, VERDICTS } from "@/hooks/use-comparison-review";
import { formatFullDate } from "@/lib/format";
import { ComparisonPair } from "./comparison-pair";

export function ComparisonTab() {
  const c = useComparisonReview();

  return (
    <QueryBoundary
      query={c.runs}
      isEmpty={(d) => !d.runs.length}
      empty={
        <EmptyState
          icon={GitCompareArrows}
          title="No comparisons"
          description="Generate one with app/backend/scripts/compare_models.py to review the official model and ShelfVision side by side."
        />
      }
    >
      {(runs) => (
        <div>
          <div className="mb-5 flex flex-wrap items-center gap-3">
            <div className="w-72">
              <Choice
                size="sm"
                value={c.runId}
                onChange={c.selectRun}
                options={runs.runs.map((r) => ({ value: r.run_id, label: `${r.run_id} · ${r.processed_count} img · ${formatFullDate(r.created_at)}` }))}
              />
            </div>
            {c.entry && (
              <span className="tnum text-sm text-muted-foreground">
                {c.index + 1} / {c.total} · {c.entry.image_name} · {Object.keys(c.done).length} revisadas
              </span>
            )}
            <div className="ml-auto flex gap-1">
              <Button variant="outline" size="icon-sm" aria-label="Previous" disabled={c.index === 0} onClick={c.prev}><ChevronLeft /></Button>
              <Button variant="outline" size="icon-sm" aria-label="Next" disabled={c.index >= c.total - 1} onClick={c.next}><ChevronRight /></Button>
            </div>
          </div>

          <QueryBoundary query={c.manifest} skeleton={<RowsSkeleton rows={3} />}>
            {() =>
              c.entry && (
                <>
                  <ComparisonPair runId={c.runId} entry={c.entry} />
                  <div className="mt-5 flex flex-wrap items-start gap-3">
                    {VERDICTS.map((v) => (
                      <Button key={v.value} variant={c.done[c.entry!.index] === v.value ? "default" : "outline"} size="sm" onClick={() => c.submit(v.value)}>
                        {v.label} <kbd className="ml-1 rounded bg-muted px-1 font-mono text-[10px] text-muted-foreground">{v.key}</kbd>
                      </Button>
                    ))}
                    <Textarea value={c.note} onChange={(e) => c.setNote(e.target.value)} placeholder="Nota opcional" className="min-h-8 flex-1 basis-60" />
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">Shortcuts: ← → navigate; 1–4 record a verdict and advance.</p>
                </>
              )
            }
          </QueryBoundary>
        </div>
      )}
    </QueryBoundary>
  );
}
