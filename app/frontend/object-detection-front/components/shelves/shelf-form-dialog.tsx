"use client";

import { Field, FormDialog } from "@/components/common/form";
import { Input } from "@/components/ui/input";
import type { ShelfDraft } from "@/hooks/use-shelf-manager";

interface Props {
  open: boolean;
  isNew: boolean;
  draft: ShelfDraft;
  busy: boolean;
  onChange: (patch: Partial<ShelfDraft>) => void;
  onSubmit: () => void;
  onClose: () => void;
}

export function ShelfFormDialog({ open, isNew, draft, busy, onChange, onSubmit, onClose }: Props) {
  return (
    <FormDialog open={open} onOpenChange={(o) => !o && onClose()} title={isNew ? "Nuevo estante" : "Editar estante"} busy={busy} onSubmit={onSubmit}>
      <Field label="Nombre" htmlFor="shelf-name">
        <Input id="shelf-name" required autoFocus value={draft.name} onChange={(e) => onChange({ name: e.target.value })} />
      </Field>
      <Field label="Zona" htmlFor="shelf-zone">
        <Input id="shelf-zone" value={draft.zone} onChange={(e) => onChange({ zone: e.target.value })} placeholder="Bebidas, lácteos…" />
      </Field>
      <Field label="Huecos tolerados" htmlFor="shelf-gap" hint="Se genera una alerta cuando una inspección supera este número. La severidad sube con el exceso.">
        <Input id="shelf-gap" type="number" min={0} value={draft.gap_threshold} onChange={(e) => onChange({ gap_threshold: e.target.value })} />
      </Field>
    </FormDialog>
  );
}
