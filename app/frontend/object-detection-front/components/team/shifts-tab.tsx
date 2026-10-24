"use client";

import { CalendarClock, Trash2 } from "lucide-react";
import { Choice } from "@/components/common/choice";
import { ConfirmDialog, Field, FormDialog } from "@/components/common/form";
import { QueryBoundary } from "@/components/common/query-boundary";
import { EmptyState, RowsSkeleton } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useEmployees, useShifts } from "@/hooks/queries/use-team";
import { useShiftManager } from "@/hooks/use-shift-manager";
import { useStoreContext } from "@/hooks/use-store-context";
import { WEEKDAYS } from "@/lib/format";
import { WeekGrid } from "./week-grid";

export function ShiftsTab({ storeId }: { storeId: string }) {
  const { canManage } = useStoreContext();
  const shifts = useShifts(storeId);
  const employees = useEmployees(storeId);
  const m = useShiftManager(storeId);
  const { draft } = m.dialog;

  const employeeName = (id: string) => employees.data?.find((e) => e.id === id)?.full_name ?? "—";

  return (
    <>
      {employees.data && !employees.data.length ? (
        <EmptyState icon={CalendarClock} title="Primero registra empleados" description="Los turnos se asignan a empleados existentes." />
      ) : (
        <QueryBoundary query={shifts} skeleton={<RowsSkeleton />}>
          {(rows) => (
            <WeekGrid
              shifts={rows}
              canManage={canManage}
              employeeName={employeeName}
              onAdd={(weekday) => m.dialog.open("new", { weekday: String(weekday) })}
              onEdit={(s) => m.dialog.open(s)}
            />
          )}
        </QueryBoundary>
      )}

      <FormDialog open={m.dialog.isOpen} onOpenChange={(o) => !o && m.dialog.close()} title={m.dialog.isNew ? "Nuevo turno" : "Editar turno"} busy={m.saving} onSubmit={m.submit}>
        <Field label="Empleado">
          <Choice value={draft.employee_id} onChange={(v) => m.dialog.patch({ employee_id: v })} disabled={!m.dialog.isNew}
            options={(employees.data ?? []).filter((e) => e.is_active || e.id === draft.employee_id).map((e) => ({ value: e.id, label: e.full_name }))} />
        </Field>
        <Field label="Día">
          <Choice value={draft.weekday} onChange={(v) => m.dialog.patch({ weekday: v })} options={WEEKDAYS.map((w, i) => ({ value: String(i), label: w }))} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Entrada" htmlFor="s-start"><Input id="s-start" type="time" required value={draft.start_time} onChange={(e) => m.dialog.patch({ start_time: e.target.value })} /></Field>
          <Field label="Salida" htmlFor="s-end"><Input id="s-end" type="time" required value={draft.end_time} onChange={(e) => m.dialog.patch({ end_time: e.target.value })} /></Field>
        </div>
        {!m.dialog.isNew && (
          <Button type="button" variant="destructive" size="sm" className="w-fit" onClick={m.askRemove}><Trash2 /> Eliminar turno</Button>
        )}
      </FormDialog>

      <ConfirmDialog
        open={!!m.removing}
        onOpenChange={(o) => !o && m.cancelRemove()}
        title="¿Eliminar turno?"
        description={m.removing ? `${WEEKDAYS[m.removing.weekday]} ${m.removing.start_time}–${m.removing.end_time} · ${employeeName(m.removing.employee_id)}` : undefined}
        confirmLabel="Eliminar"
        destructive
        onConfirm={m.confirmRemove}
      />
    </>
  );
}
