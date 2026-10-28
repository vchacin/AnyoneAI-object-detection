import { request } from "@/lib/api/client";
import type { Store, StoreSettings } from "@/lib/api/types";

export interface CreateStoreInput {
  name: string;
  address?: string | null;
  admin_email?: string | null;
  admin_password?: string | null;
}

export const storesService = {
  list: () => request<Store[]>("/stores"),
  get: (id: string) => request<Store>(`/stores/${id}`),
  create: (json: CreateStoreInput) => request<Store>("/stores", { method: "POST", json }),
  update: (id: string, json: Partial<Pick<Store, "name" | "address" | "status">>) =>
    request<Store>(`/stores/${id}`, { method: "PATCH", json }),
  settings: (id: string) => request<StoreSettings>(`/stores/${id}/settings`),
  updateSettings: (id: string, json: Partial<Omit<StoreSettings, "store_id">>) =>
    request<StoreSettings>(`/stores/${id}/settings`, { method: "PUT", json }),
};
