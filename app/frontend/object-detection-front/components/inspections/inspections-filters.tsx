"use client";

import { Choice } from "@/components/common/choice";
import { Field } from "@/components/common/form";
import { Input } from "@/components/ui/input";
import type { Camera, Shelf } from "@/lib/api/types";

interface Props {
  cameras?: Camera[];
  shelves?: Shelf[];
  /** Solo hay camaras/estantes con una tienda en contexto. */
  showScope: boolean;
  values: { cameraId: string; shelfId: string; from: string; to: string };
  onCamera: (v: string) => void;
  onShelf: (v: string) => void;
  onFrom: (v: string) => void;
  onTo: (v: string) => void;
}

export function InspectionsFilters({ cameras, shelves, showScope, values, onCamera, onShelf, onFrom, onTo }: Props) {
  return (
    <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {showScope && (
        <>
          <Field label="Cámara">
            <Choice size="sm" value={values.cameraId} onChange={onCamera} emptyLabel="Todas"
              options={(cameras ?? []).map((c) => ({ value: c.id, label: c.name }))} />
          </Field>
          <Field label="Estante">
            <Choice size="sm" value={values.shelfId} onChange={onShelf} emptyLabel="Todos"
              options={(shelves ?? []).map((s) => ({ value: s.id, label: s.name }))} />
          </Field>
        </>
      )}
      <Field label="Desde">
        <Input type="date" className="h-7" value={values.from} onChange={(e) => onFrom(e.target.value)} />
      </Field>
      <Field label="Hasta">
        <Input type="date" className="h-7" value={values.to} onChange={(e) => onTo(e.target.value)} />
      </Field>
    </div>
  );
}
