"use client";

import { useCreateEmployee, useUpdateEmployee } from "@/hooks/queries/use-team";
import { useEditDialog } from "@/hooks/use-edit-dialog";
import type { Employee } from "@/lib/api/types";

export interface EmployeeDraft {
  full_name: string;
  position: string;
  user_id: string;
  active: boolean;
}

const toDraft = (e: Employee | null): EmployeeDraft => ({
  full_name: e?.full_name ?? "",
  position: e?.position ?? "",
  user_id: e?.user_id ?? "",
  active: e?.is_active ?? true,
});

export function useEmployeeManager(storeId: string) {
  const dialog = useEditDialog<Employee, EmployeeDraft>(toDraft);
  const create = useCreateEmployee(storeId);
  const update = useUpdateEmployee(storeId);

  async function save() {
    const { full_name, position, user_id, active } = dialog.draft;
    const common = { full_name: full_name.trim(), position: position.trim() || null };
    try {
      if (dialog.item) await update.mutateAsync({ id: dialog.item.id, ...common, is_active: active });
      else await create.mutateAsync({ ...common, user_id: user_id || null });
      dialog.close();
    } catch {
      /* toast global */
    }
  }

  return { dialog, save, saving: create.isPending || update.isPending };
}
