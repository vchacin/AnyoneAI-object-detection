import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Shift } from "@/lib/api/types";
import { WEEKDAYS } from "@/lib/format";

interface Props {
  shifts: Shift[];
  canManage: boolean;
  employeeName: (id: string) => string;
  onAdd: (weekday: number) => void;
  onEdit: (shift: Shift) => void;
}

/** Horario semanal: una columna por dia, un bloque por turno. */
export function WeekGrid({ shifts, canManage, employeeName, onAdd, onEdit }: Props) {
  return (
    <div className="grid divide-y rounded-lg border sm:grid-cols-7 sm:divide-x sm:divide-y-0">
      {WEEKDAYS.map((day, i) => {
        const list = shifts.filter((s) => s.weekday === i).sort((a, b) => a.start_time.localeCompare(b.start_time));
        return (
          <div key={day} className="flex min-h-28 flex-col gap-1.5 p-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">{day.slice(0, 3)}</span>
              {canManage && (
                <Button variant="ghost" size="icon-xs" aria-label={`Añadir turno el ${day}`} onClick={() => onAdd(i)}><Plus /></Button>
              )}
            </div>
            {list.map((s) => (
              <button
                key={s.id}
                disabled={!canManage}
                onClick={() => onEdit(s)}
                className="rounded-md bg-primary/10 px-2 py-1.5 text-left text-xs outline-none enabled:hover:bg-primary/20 focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span className="tnum block font-semibold text-primary">{s.start_time}–{s.end_time}</span>
                <span className="block truncate">{employeeName(s.employee_id)}</span>
              </button>
            ))}
          </div>
        );
      })}
    </div>
  );
}
