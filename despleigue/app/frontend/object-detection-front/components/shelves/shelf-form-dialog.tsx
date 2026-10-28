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
    <FormDialog open={open} onOpenChange={(o) => !o && onClose()} title={isNew ? "New shelf" : "Edit shelf"} busy={busy} onSubmit={onSubmit}>
      <Field label="Name" htmlFor="shelf-name">
        <Input id="shelf-name" required autoFocus value={draft.name} onChange={(e) => onChange({ name: e.target.value })} />
      </Field>
      <Field label="Zone" htmlFor="shelf-zone">
        <Input id="shelf-zone" value={draft.zone} onChange={(e) => onChange({ zone: e.target.value })} placeholder="Drinks, dairy…" />
      </Field>
      <Field label="Allowed gaps" htmlFor="shelf-gap" hint="An alert is created when an inspection exceeds this number. Severity increases with the excess.">
        <Input id="shelf-gap" type="number" min={0} value={draft.gap_threshold} onChange={(e) => onChange({ gap_threshold: e.target.value })} />
      </Field>
    </FormDialog>
  );
}
