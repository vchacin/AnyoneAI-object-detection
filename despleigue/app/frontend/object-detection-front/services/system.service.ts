import { request } from "@/lib/api/client";
import type { ComparisonManifest, ComparisonRun, Health, ModelCatalog, PredictResponse, Verdict } from "@/lib/api/types";

export interface PredictInput {
  file: File;
  model?: string;
  persist?: boolean;
  conf?: number | null;
  camera_id?: string | null;
  shelf_id?: string | null;
  /** Solo lo usa un super_admin para elegir donde se guarda la inspeccion. */
  store_id?: string | null;
}

export const systemService = {
  health: () => request<Health>("/health"),
  models: () => request<ModelCatalog>("/models"),

  predict: ({ file, model, persist = true, conf, camera_id, shelf_id, store_id }: PredictInput) => {
    const body = new FormData();
    body.append("image", file);
    if (camera_id) body.append("camera_id", camera_id);
    if (shelf_id) body.append("shelf_id", shelf_id);
    if (store_id) body.append("store_id", store_id);
    if (conf !== null && conf !== undefined) body.append("conf", String(conf));
    return request<PredictResponse>("/inference", {
      method: "POST",
      query: { model: model || undefined, persist },
      body,
    });
  },

  comparisons: () => request<{ runs: ComparisonRun[] }>("/comparisons", { anonymous: true }),
  comparisonManifest: (runId: string) =>
    request<ComparisonManifest>(`/comparisons/${runId}/manifest`, { anonymous: true }),
  reviewComparison: (runId: string, json: { index: number; verdict: Verdict; note?: string }) =>
    request<{ ok: boolean }>(`/comparisons/${runId}/review`, { method: "POST", json, anonymous: true }),
};
