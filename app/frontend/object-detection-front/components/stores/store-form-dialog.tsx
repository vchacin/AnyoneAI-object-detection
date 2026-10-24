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
    <FormDialog open={open} onOpenChange={(o) => !o && onClose()} title={isNew ? "Nueva tienda" : "Editar tienda"} busy={busy} onSubmit={onSubmit}>
      <Field label="Nombre" htmlFor="st-name">
        <Input id="st-name" required autoFocus value={draft.name} onChange={(e) => onChange({ name: e.target.value })} />
      </Field>
      <Field label="Dirección" htmlFor="st-addr">
        <Input id="st-addr" value={draft.address} onChange={(e) => onChange({ address: e.target.value })} />
      </Field>
      {isNew ? (
        <div className="grid gap-4 border-t pt-4">
          <p className="text-xs text-muted-foreground">Administrador inicial (opcional)</p>
          <Field label="Correo" htmlFor="st-mail">
            <Input id="st-mail" type="email" value={draft.admin_email} onChange={(e) => onChange({ admin_email: e.target.value })} />
          </Field>
          <Field label="Contraseña" htmlFor="st-pass" hint="Mínimo 8 caracteres.">
            <Input id="st-pass" type="password" minLength={8} autoComplete="new-password" value={draft.admin_password} onChange={(e) => onChange({ admin_password: e.target.value })} />
          </Field>
        </div>
      ) : (
        <Field label="Estado">
          <Choice value={draft.status} onChange={(v) => onChange({ status: v })} options={[{ value: "active", label: "Activa" }, { value: "inactive", label: "Inactiva" }]} />
        </Field>
      )}
    </FormDialog>
  );
}
