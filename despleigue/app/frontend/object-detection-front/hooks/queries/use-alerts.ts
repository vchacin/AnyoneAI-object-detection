"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { AlertStatus } from "@/lib/api/types";
import { alertsService } from "@/services/alerts.service";
import { qk } from "./keys";

export function useAlerts(storeId: string, filters: { status: string; severity: string }) {
  return useQuery({
    queryKey: qk.alertList(storeId, filters),
    queryFn: () => alertsService.list(storeId, { ...filters, limit: 100 }),
  });
}

/** Number of open alerts; refreshed every minute for the menu badge. */
export function useOpenAlertCount(storeId: string | null) {
  return useQuery({
    queryKey: qk.alertCount(storeId ?? ""),
    queryFn: () => alertsService.count(storeId!),
    enabled: !!storeId,
    select: (r) => r.count,
    refetchInterval: 60_000,
  });
}

export function useTransitionAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: Exclude<AlertStatus, "open"> }) =>
      alertsService.update(id, status),
    onSuccess: (alert) => {
      toast.success(alert.status === "closed" ? "Alert closed" : "Alert acknowledged");
      return Promise.all([qc.invalidateQueries({ queryKey: qk.alerts }), qc.invalidateQueries({ queryKey: ["dashboard"] })]);
    },
  });
}
