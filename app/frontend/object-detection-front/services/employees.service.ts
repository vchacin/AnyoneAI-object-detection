import { request } from "@/lib/api/client";
import type { Employee } from "@/lib/api/types";

export const employeesService = {
  list: (storeId: string) => request<Employee[]>(`/stores/${storeId}/employees`),
  create: (storeId: string, json: { full_name: string; position?: string | null; user_id?: string | null }) =>
    request<Employee>(`/stores/${storeId}/employees`, { method: "POST", json }),
  update: (id: string, json: Partial<Pick<Employee, "full_name" | "position" | "is_active">>) =>
    request<Employee>(`/employees/${id}`, { method: "PATCH", json }),
};
