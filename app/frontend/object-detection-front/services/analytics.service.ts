import { request } from "@/lib/api/client";
import type { GlobalDashboard, StoreDashboard, UsageMetrics } from "@/lib/api/types";

export const analyticsService = {
  globalDashboard: () => request<GlobalDashboard>("/dashboard/global"),
  storeDashboard: (storeId: string) => request<StoreDashboard>(`/stores/${storeId}/dashboard`),
  usage: (query: { store_id?: string | null; date_from?: string | null; date_to?: string | null }) =>
    request<UsageMetrics>("/metrics/usage", { query }),
};
