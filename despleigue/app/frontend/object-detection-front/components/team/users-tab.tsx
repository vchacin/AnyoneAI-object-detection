"use client";

import { Pencil, Plus, UserCog } from "lucide-react";
import { ActivePill, ROLE_LABELS } from "@/components/common/badges";
import { Choice } from "@/components/common/choice";
import { Field, FormDialog } from "@/components/common/form";
import { QueryBoundary } from "@/components/common/query-boundary";
import { EmptyState, RowsSkeleton } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useUsers } from "@/hooks/queries/use-team";
import { useStoreContext } from "@/hooks/use-store-context";
import { useUserManager } from "@/hooks/use-user-manager";

const ROLES = ["store_admin", "employee", "viewer"].map((r) => ({ value: r, label: ROLE_LABELS[r] }));

export function UsersTab({ storeId }: { storeId: string }) {
  const { canManage } = useStoreContext();
  const users = useUsers(storeId);
  const { dialog, save, saving } = useUserManager(storeId);
  const { draft } = dialog;

  return (
    <>
      {canManage && (
        <div className="mb-4 flex justify-end">
          <Button size="sm" onClick={() => dialog.open("new")}><Plus /> New user</Button>
        </div>
      )}
      <QueryBoundary
        query={users}
        skeleton={<RowsSkeleton />}
        isEmpty={(rows) => !rows.length}
        empty={<EmptyState icon={UserCog} title="No users" description="Create accounts so your team can access the dashboard." />}
      >
        {(rows) => (
          <Table>
            <TableHeader>
              <TableRow><TableHead>Email</TableHead><TableHead>Role</TableHead><TableHead>Status</TableHead><TableHead className="w-0" /></TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-medium">{u.email}</TableCell>
                  <TableCell className="text-muted-foreground">{ROLE_LABELS[u.role] ?? u.role}</TableCell>
                  <TableCell><ActivePill active={u.is_active} /></TableCell>
                  <TableCell>
                    {canManage && (
                      <div className="flex justify-end">
                        <Button variant="ghost" size="icon-sm" aria-label="Edit" onClick={() => dialog.open(u)}><Pencil /></Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </QueryBoundary>

      <FormDialog open={dialog.isOpen} onOpenChange={(o) => !o && dialog.close()} title={dialog.isNew ? "New user" : "Edit user"} busy={saving} onSubmit={save}>
        {dialog.isNew && (
          <Field label="Email" htmlFor="u-email">
            <Input id="u-email" type="email" required autoFocus value={draft.email} onChange={(e) => dialog.patch({ email: e.target.value })} />
          </Field>
        )}
        <Field label={dialog.isNew ? "Password" : "New password"} htmlFor="u-pass" hint={dialog.isNew ? "At least 8 characters." : "Leave blank to keep the current password."}>
          <Input id="u-pass" type="password" minLength={8} required={dialog.isNew} autoComplete="new-password" value={draft.password} onChange={(e) => dialog.patch({ password: e.target.value })} />
        </Field>
        <Field label="Role"><Choice value={draft.role} onChange={(v) => dialog.patch({ role: v })} options={ROLES} /></Field>
        {!dialog.isNew && (
          <Field label="Status">
            <Choice value={draft.active ? "1" : "0"} onChange={(v) => dialog.patch({ active: v === "1" })} options={[{ value: "1", label: "Active" }, { value: "0", label: "Inactive" }]} />
          </Field>
        )}
      </FormDialog>
    </>
  );
}
