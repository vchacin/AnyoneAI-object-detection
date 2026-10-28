"use client";

import { Choice } from "@/components/common/choice";
import { Field, FormDialog } from "@/components/common/form";
import { Input } from "@/components/ui/input";
import type { StoreDraft } from "@/hooks/use-store-manager";

interface Props {
  open: boolean;
  isNew: boolean;
  draft: StoreDraft;
  busy: boolean;
  onChange: (patch: Partial<StoreDraft>) => void;
  onSubmit: () => void;
  onClose: () => void;
}

export function StoreFormDialog({ open, isNew, draft, busy, onChange, onSubmit, onClose }: Props) {
  return (
    <FormDialog open={open} onOpenChange={(o) => !o && onClose()} title={isNew ? "New store" : "Edit store"} busy={busy} onSubmit={onSubmit}>
      <Field label="Name" htmlFor="st-name">
        <Input id="st-name" required autoFocus value={draft.name} onChange={(e) => onChange({ name: e.target.value })} />
      </Field>
      <Field label="Address" htmlFor="st-addr">
        <Input id="st-addr" value={draft.address} onChange={(e) => onChange({ address: e.target.value })} />
      </Field>
      {isNew ? (
        <div className="grid gap-4 border-t pt-4">
          <p className="text-xs text-muted-foreground">Initial administrator (optional)</p>
          <Field label="Email" htmlFor="st-mail">
            <Input id="st-mail" type="email" value={draft.admin_email} onChange={(e) => onChange({ admin_email: e.target.value })} />
          </Field>
          <Field label="Password" htmlFor="st-pass" hint="At least 8 characters.">
            <Input id="st-pass" type="password" minLength={8} autoComplete="new-password" value={draft.admin_password} onChange={(e) => onChange({ admin_password: e.target.value })} />
          </Field>
        </div>
      ) : (
        <Field label="Status">
          <Choice value={draft.status} onChange={(v) => onChange({ status: v })} options={[{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }]} />
        </Field>
      )}
    </FormDialog>
  );
}
