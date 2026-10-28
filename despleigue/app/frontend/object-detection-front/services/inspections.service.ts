import { download, request, requestBlob } from "@/lib/api/client";
import type { Inspection } from "@/lib/api/types";

export type InspectionFilters = {
  store_id?: string | null;
  camera_id?: string | null;
  shelf_id?: string | null;
  date_from?: string | null;
  date_to?: string | null;
};

export const inspectionsService = {
  list: (query: InspectionFilters & { limit?: number; offset?: number }) =>
    request<Inspection[]>("/inspections", { query }),
  get: (id: string) => request<Inspection>(`/inspections/${id}`),
  remove: (id: string) => request<void>(`/inspections/${id}`, { method: "DELETE" }),
  image: (id: string) => requestBlob(`/inspections/${id}/image`),
  exportOne: (id: string) => download(`/inspections/${id}/export`, `${id}.json`),
  exportMany: (query: Omit<InspectionFilters, "camera_id"> & { limit?: number }) =>
    download("/inspections/export", "inspections.jsonl", query),
};
