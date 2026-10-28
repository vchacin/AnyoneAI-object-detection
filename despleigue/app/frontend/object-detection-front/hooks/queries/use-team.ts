"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { employeesService } from "@/services/employees.service";
import { type ShiftInput, shiftsService } from "@/services/shifts.service";
import { usersService } from "@/services/users.service";
import { qk } from "./keys";

/* ------------------------------ users ------------------------------ */

export function useUsers(storeId: string) {
  return useQuery({ queryKey: qk.users(storeId), queryFn: () => usersService.list(storeId) });
}

export function useCreateUser(storeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string; role: string }) => usersService.create(storeId, body),
    meta: { success: "User creado" },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.users(storeId) }),
  });
}

export function useUpdateUser(storeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; role?: string; password?: string; is_active?: boolean }) =>
      usersService.update(storeId, id, body),
    meta: { success: "User actualizado" },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.users(storeId) }),
  });
}

/* ------------------------------ empleados ------------------------------ */

export function useEmployees(storeId: string) {
  return useQuery({ queryKey: qk.employees(storeId), queryFn: () => employeesService.list(storeId) });
}

export function useCreateEmployee(storeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { full_name: string; position?: string | null; user_id?: string | null }) =>
      employeesService.create(storeId, body),
    meta: { success: "Employee creado" },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.employees(storeId) }),
  });
}

export function useUpdateEmployee(storeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; full_name?: string; position?: string | null; is_active?: boolean }) =>
      employeesService.update(id, body),
    meta: { success: "Employee actualizado" },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.employees(storeId) }),
  });
}

/* -------------------------------- shifts -------------------------------- */

export function useShifts(storeId: string) {
  return useQuery({ queryKey: qk.shifts(storeId), queryFn: () => shiftsService.list(storeId) });
}

export function useSaveShift(storeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: ShiftInput & { id?: string }) =>
      id ? shiftsService.update(id, body) : shiftsService.create(body),
    meta: { success: "Shift saved" },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.shifts(storeId) }),
  });
}

export function useDeleteShift(storeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => shiftsService.remove(id),
    meta: { success: "Shift deleted" },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.shifts(storeId) }),
  });
}
