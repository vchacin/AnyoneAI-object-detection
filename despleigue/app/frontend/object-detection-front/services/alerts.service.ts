import { request } from "@/lib/api/client";
import type { Alert, AlertStatus } from "@/lib/api/types";

export const alertsService = {
  list: (storeId: string, query: { status?: string | null; severity?: string | null; limit?: number; offset?: number }) =>
    request<Alert[]>(`/stores/${storeId}/alerts`, { query }),
  count: (storeId: string, status = "open") =>
    request<{ store_id: string; status: string; count: number }>(`/stores/${storeId}/alerts/count`, {
      query: { status },
    }),
  update: (id: string, status: Exclude<AlertStatus, "open">) =>
    request<Alert>(`/alerts/${id}`, { method: "PATCH", json: { status } }),
};
