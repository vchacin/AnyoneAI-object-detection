"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type InspectionFilters, inspectionsService } from "@/services/inspections.service";
import { qk } from "./keys";

export function useInspections(filters: InspectionFilters, page: number, pageSize: number) {
  const params = { ...filters, limit: pageSize, offset: page * pageSize };
  return useQuery({
    queryKey: qk.inspectionList(params),
    queryFn: () => inspectionsService.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useInspection(id: string | null) {
  return useQuery({ queryKey: qk.inspection(id ?? ""), queryFn: () => inspectionsService.get(id!), enabled: !!id });
}

/** Downloads the image with credentials and exposes it as an object URL. */
export function useInspectionImage(id: string | null) {
  return useQuery({
    queryKey: qk.inspectionImage(id ?? ""),
    queryFn: async () => URL.createObjectURL(await inspectionsService.image(id!)),
    enabled: !!id,
    staleTime: Infinity,
    gcTime: 5 * 60_000,
    retry: false,
  });
}

export function useDeleteInspection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => inspectionsService.remove(id),
    meta: { success: "Inspection deleted" },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.inspections }),
  });
}

export function useExportInspections() {
  return useMutation({
    mutationFn: (filters: Parameters<typeof inspectionsService.exportMany>[0]) =>
      inspectionsService.exportMany({ ...filters, limit: 10000 }),
  });
}

export function useExportInspection() {
  return useMutation({ mutationFn: (id: string) => inspectionsService.exportOne(id) });
}
