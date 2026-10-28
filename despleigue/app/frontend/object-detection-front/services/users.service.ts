import { request } from "@/lib/api/client";
import type { StoreUser } from "@/lib/api/types";

export const usersService = {
  list: (storeId: string) => request<StoreUser[]>(`/stores/${storeId}/users`),
  create: (storeId: string, json: { email: string; password: string; role: string }) =>
    request<StoreUser>(`/stores/${storeId}/users`, { method: "POST", json }),
  update: (storeId: string, id: string, json: { role?: string; password?: string; is_active?: boolean }) =>
    request<StoreUser>(`/stores/${storeId}/users/${id}`, { method: "PATCH", json }),
};
