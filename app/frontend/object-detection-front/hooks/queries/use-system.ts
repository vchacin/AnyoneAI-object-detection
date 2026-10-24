"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Verdict } from "@/lib/api/types";
import { type PredictInput, systemService } from "@/services/system.service";
import { qk } from "./keys";

export function useHealth() {
  return useQuery({ queryKey: qk.health, queryFn: systemService.health });
}

export function useModels() {
  return useQuery({ queryKey: qk.models, queryFn: systemService.models, staleTime: 5 * 60_000 });
}

export function usePredict() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: PredictInput) => systemService.predict(input),
    onSuccess: (res) => {
      if (res.inspection_id) {
        void qc.invalidateQueries({ queryKey: qk.inspections });
        void qc.invalidateQueries({ queryKey: qk.alerts });
        void qc.invalidateQueries({ queryKey: ["dashboard"] });
      }
    },
  });
}

export function useComparisonRuns() {
  return useQuery({ queryKey: qk.comparisons, queryFn: systemService.comparisons });
}

export function useComparison(runId: string) {
  return useQuery({
    queryKey: qk.comparison(runId),
    queryFn: () => systemService.comparisonManifest(runId),
    enabled: !!runId,
  });
}

export function useReviewComparison(runId: string) {
  return useMutation({
    mutationFn: (body: { index: number; verdict: Verdict; note?: string }) => systemService.reviewComparison(runId, body),
  });
}
