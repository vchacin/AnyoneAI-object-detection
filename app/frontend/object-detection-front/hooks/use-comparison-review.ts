"use client";

import { useCallback, useEffect, useState } from "react";
import { useComparison, useComparisonRuns, useReviewComparison } from "@/hooks/queries/use-system";
import type { Verdict } from "@/lib/api/types";

export const VERDICTS: { value: Verdict; label: string; key: string }[] = [
  { value: "official", label: "Gana oficial", key: "1" },
  { value: "shelfvision", label: "Gana ShelfVision", key: "2" },
  { value: "tie", label: "Empate", key: "3" },
  { value: "unclear", label: "No claro", key: "4" },
];

/** Estado de la revision: corrida elegida, entrada actual, veredictos y atajos de teclado. */
export function useComparisonReview() {
  const runs = useComparisonRuns();
  const [chosenRun, setChosenRun] = useState("");
  const [index, setIndex] = useState(0);
  const [note, setNote] = useState("");
  const [done, setDone] = useState<Record<number, Verdict>>({});

  const runId = chosenRun || runs.data?.runs[0]?.run_id || "";
  const manifest = useComparison(runId);
  const review = useReviewComparison(runId);

  const entries = manifest.data?.entries ?? [];
  const entry = entries[index];
  const last = entries.length - 1;

  const selectRun = (id: string) => {
    setChosenRun(id);
    setIndex(0);
    setDone({});
  };

  const submit = useCallback(
    async (verdict: Verdict) => {
      if (!entry) return;
      try {
        await review.mutateAsync({ index: entry.index, verdict, note });
        setDone((d) => ({ ...d, [entry.index]: verdict }));
        setNote("");
        setIndex((i) => Math.min(last, i + 1));
      } catch {
        /* toast global */
      }
    },
    [entry, review, note, last],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName ?? "")) return;
      if (e.key === "ArrowLeft") setIndex((i) => Math.max(0, i - 1));
      if (e.key === "ArrowRight") setIndex((i) => Math.min(last, i + 1));
      const v = VERDICTS.find((x) => x.key === e.key);
      if (v) void submit(v.value);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [last, submit]);

  return {
    runs,
    runId,
    selectRun,
    manifest,
    entry,
    total: entries.length,
    index,
    setIndex,
    note,
    setNote,
    done,
    submit,
    prev: () => setIndex((i) => Math.max(0, i - 1)),
    next: () => setIndex((i) => Math.min(last, i + 1)),
  };
}
