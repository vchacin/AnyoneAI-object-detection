import { request } from "@/lib/api/client";
import type { Shelf } from "@/lib/api/types";

export interface ShelfInput {
  name: string;
  zone?: string | null;
  gap_threshold?: number;
}

export const shelvesService = {
  list: (storeId: string) => request<Shelf[]>(`/stores/${storeId}/shelves`),
  create: (storeId: string, json: ShelfInput) =>
    request<Shelf>(`/stores/${storeId}/shelves`, { method: "POST", json }),
  update: (storeId: string, id: string, json: Partial<ShelfInput>) =>
    request<Shelf>(`/stores/${storeId}/shelves/${id}`, { method: "PATCH", json }),
};
