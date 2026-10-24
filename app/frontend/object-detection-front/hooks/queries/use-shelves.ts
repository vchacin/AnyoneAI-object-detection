"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ShelfInput, shelvesService } from "@/services/shelves.service";
import { qk } from "./keys";

export function useShelves(storeId: string | null) {
  return useQuery({ queryKey: qk.shelves(storeId ?? ""), queryFn: () => shelvesService.list(storeId!), enabled: !!storeId });
}

export function useCreateShelf(storeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ShelfInput) => shelvesService.create(storeId, input),
    meta: { success: "Estante creado" },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.shelves(storeId) }),
  });
}

export function useUpdateShelf(storeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Partial<ShelfInput>) => shelvesService.update(storeId, id, body),
    meta: { success: "Estante actualizado" },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.shelves(storeId) }),
  });
}
