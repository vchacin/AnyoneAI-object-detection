"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsService } from "@/services/analytics.service";
import { qk } from "./keys";

export function useGlobalDashboard() {
  return useQuery({ queryKey: qk.dashboardGlobal, queryFn: analyticsService.globalDashboard });
}

export function useStoreDashboard(storeId: string) {
  return useQuery({ queryKey: qk.dashboardStore(storeId), queryFn: () => analyticsService.storeDashboard(storeId) });
}

export function useUsage(storeId: string | null) {
  return useQuery({ queryKey: qk.usage(storeId), queryFn: () => analyticsService.usage({ store_id: storeId }) });
}
