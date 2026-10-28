"use client";

import { Choice } from "@/components/common/choice";
import { Field } from "@/components/common/form";
import { Input } from "@/components/ui/input";
import type { Camera, Shelf } from "@/lib/api/types";

interface Props {
  cameras?: Camera[];
  shelves?: Shelf[];
  /** Only cameras/shelves belonging to the store in context. */
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
          <Field label="Camera">
            <Choice size="sm" value={values.cameraId} onChange={onCamera} emptyLabel="All"
              options={(cameras ?? []).map((c) => ({ value: c.id, label: c.name }))} />
          </Field>
          <Field label="Shelf">
            <Choice size="sm" value={values.shelfId} onChange={onShelf} emptyLabel="All"
              options={(shelves ?? []).map((s) => ({ value: s.id, label: s.name }))} />
          </Field>
        </>
      )}
      <Field label="From">
        <Input type="date" className="h-7" value={values.from} onChange={(e) => onFrom(e.target.value)} />
      </Field>
      <Field label="To">
        <Input type="date" className="h-7" value={values.to} onChange={(e) => onTo(e.target.value)} />
      </Field>
    </div>
  );
}
