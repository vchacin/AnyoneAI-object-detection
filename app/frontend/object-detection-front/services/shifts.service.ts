import { request } from "@/lib/api/client";
import type { Shift } from "@/lib/api/types";

export type ShiftInput = Omit<Shift, "id" | "store_id">;

export const shiftsService = {
  list: (storeId: string) => request<Shift[]>(`/stores/${storeId}/shifts`),
  create: (json: ShiftInput) => request<Shift>(`/employees/${json.employee_id}/shifts`, { method: "POST", json }),
  update: (id: string, json: ShiftInput) => request<Shift>(`/shifts/${id}`, { method: "PATCH", json }),
  remove: (id: string) => request<void>(`/shifts/${id}`, { method: "DELETE" }),
};
