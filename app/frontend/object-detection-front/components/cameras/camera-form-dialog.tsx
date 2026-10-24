"use client";

import { Choice } from "@/components/common/choice";
import { Field, FormDialog } from "@/components/common/form";
import { Input } from "@/components/ui/input";
import type { CameraDraft } from "@/hooks/use-camera-manager";
import type { Shelf } from "@/lib/api/types";

interface Props {
  open: boolean;
  isNew: boolean;
  draft: CameraDraft;
  shelves: Shelf[];
  busy: boolean;
  onChange: (patch: Partial<CameraDraft>) => void;
  onSubmit: () => void;
  onClose: () => void;
}

export function CameraFormDialog({ open, isNew, draft, shelves, busy, onChange, onSubmit, onClose }: Props) {
  return (
    <FormDialog open={open} onOpenChange={(o) => !o && onClose()} title={isNew ? "Nueva cámara" : "Editar cámara"} busy={busy} onSubmit={onSubmit}>
      <Field label="Nombre" htmlFor="cam-name">
        <Input id="cam-name" required autoFocus value={draft.name} onChange={(e) => onChange({ name: e.target.value })} />
      </Field>
      <Field label="Ubicación" htmlFor="cam-loc">
        <Input id="cam-loc" value={draft.location} onChange={(e) => onChange({ location: e.target.value })} placeholder="Pasillo 3, lado izquierdo" />
      </Field>
      <Field label="Estante vinculado">
        <Choice value={draft.shelf_id} onChange={(v) => onChange({ shelf_id: v })} emptyLabel="Ninguno"
          options={shelves.map((s) => ({ value: s.id, label: s.name }))} />
      </Field>
      {!isNew && (
        <Field label="Estado">
          <Choice value={draft.active ? "active" : "inactive"} onChange={(v) => onChange({ active: v === "active" })}
            options={[{ value: "active", label: "Activa" }, { value: "inactive", label: "Inactiva" }]} />
        </Field>
      )}
    </FormDialog>
  );
}
