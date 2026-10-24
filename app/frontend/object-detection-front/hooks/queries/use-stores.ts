"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { StoreSettings } from "@/lib/api/types";
import { type CreateStoreInput, storesService } from "@/services/stores.service";
import { useAuth } from "@/stores/auth-store";
import { qk } from "./keys";

/** Lista de tiendas. Solo super_admin puede pedirla. */
export function useStoresQuery(enabled = true) {
  return useQuery({ queryKey: qk.stores, queryFn: storesService.list, enabled });
}

export function useStoreQuery(id: string | null) {
  return useQuery({ queryKey: qk.store(id ?? ""), queryFn: () => storesService.get(id!), enabled: !!id });
}

export function useCreateStore() {
  const qc = useQueryClient();
  const setActiveStore = useAuth((s) => s.setActiveStore);
  return useMutation({
    mutationFn: (input: CreateStoreInput) => storesService.create(input),
    meta: { success: "Tienda creada" },
    onSuccess: (store) => {
      setActiveStore(store.id);
      return qc.invalidateQueries({ queryKey: qk.stores });
    },
  });
}

export function useUpdateStore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; name?: string; address?: string | null; status?: string }) =>
      storesService.update(id, body),
    meta: { success: "Tienda actualizada" },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.stores }),
  });
}

export function useStoreSettings(storeId: string) {
  return useQuery({ queryKey: qk.storeSettings(storeId), queryFn: () => storesService.settings(storeId) });
}

export function useUpdateSettings(storeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Omit<StoreSettings, "store_id">>) => storesService.updateSettings(storeId, body),
    meta: { success: "Ajustes guardados" },
    onSuccess: (data) => qc.setQueryData(qk.storeSettings(storeId), data),
  });
}
