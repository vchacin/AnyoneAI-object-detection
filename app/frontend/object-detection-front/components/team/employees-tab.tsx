"use client";

import { Pencil, Plus, Users } from "lucide-react";
import { ActivePill } from "@/components/common/badges";
import { Choice } from "@/components/common/choice";
import { Field, FormDialog } from "@/components/common/form";
import { QueryBoundary } from "@/components/common/query-boundary";
import { EmptyState, RowsSkeleton } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useEmployees, useUsers } from "@/hooks/queries/use-team";
import { useEmployeeManager } from "@/hooks/use-employee-manager";
import { useStoreContext } from "@/hooks/use-store-context";

export function EmployeesTab({ storeId }: { storeId: string }) {
  const { canManage } = useStoreContext();
  const employees = useEmployees(storeId);
  const users = useUsers(storeId);
  const { dialog, save, saving } = useEmployeeManager(storeId);
  const { draft } = dialog;

  const userEmail = (id: string | null) => users.data?.find((u) => u.id === id)?.email;

  return (
    <>
      {canManage && (
        <div className="mb-4 flex justify-end">
          <Button size="sm" onClick={() => dialog.open("new")}><Plus /> Nuevo empleado</Button>
        </div>
      )}
      <QueryBoundary
        query={employees}
        skeleton={<RowsSkeleton />}
        isEmpty={(rows) => !rows.length}
        empty={<EmptyState icon={Users} title="Sin empleados" description="Registra al personal para asignarle turnos." />}
      >
        {(rows) => (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead><TableHead>Cargo</TableHead>
                <TableHead className="hidden sm:table-cell">Usuario</TableHead><TableHead>Estado</TableHead><TableHead className="w-0" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((e) => (
                <TableRow key={e.id}>
                  <TableCell className="font-medium">{e.full_name}</TableCell>
                  <TableCell className="text-muted-foreground">{e.position ?? "—"}</TableCell>
                  <TableCell className="hidden text-muted-foreground sm:table-cell">{userEmail(e.user_id) ?? "—"}</TableCell>
                  <TableCell><ActivePill active={e.is_active} /></TableCell>
                  <TableCell>
                    {canManage && (
                      <div className="flex justify-end">
                        <Button variant="ghost" size="icon-sm" aria-label="Editar" onClick={() => dialog.open(e)}><Pencil /></Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </QueryBoundary>

      <FormDialog open={dialog.isOpen} onOpenChange={(o) => !o && dialog.close()} title={dialog.isNew ? "Nuevo empleado" : "Editar empleado"} busy={saving} onSubmit={save}>
        <Field label="Nombre completo" htmlFor="e-name">
          <Input id="e-name" required autoFocus value={draft.full_name} onChange={(e) => dialog.patch({ full_name: e.target.value })} />
        </Field>
        <Field label="Cargo" htmlFor="e-pos">
          <Input id="e-pos" value={draft.position} onChange={(e) => dialog.patch({ position: e.target.value })} placeholder="Reponedor, supervisor…" />
        </Field>
        {dialog.isNew ? (
          <Field label="Usuario vinculado" hint="Opcional: permite que atienda alertas con su cuenta.">
            <Choice value={draft.user_id} onChange={(v) => dialog.patch({ user_id: v })} emptyLabel="Ninguno"
              options={(users.data ?? []).map((u) => ({ value: u.id, label: u.email }))} />
          </Field>
        ) : (
          <Field label="Estado">
            <Choice value={draft.active ? "1" : "0"} onChange={(v) => dialog.patch({ active: v === "1" })}
              options={[{ value: "1", label: "Activo" }, { value: "0", label: "Inactivo" }]} />
          </Field>
        )}
      </FormDialog>
    </>
  );
}
