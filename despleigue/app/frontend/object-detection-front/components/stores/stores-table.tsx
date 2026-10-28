import { ArrowRightLeft, Pencil } from "lucide-react";
import { StatusPill } from "@/components/common/badges";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Store } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface Props {
  stores: Store[];
  activeId: string | null;
  onOpen: (store: Store) => void;
  onEdit: (store: Store) => void;
}

export function StoresTable({ stores, activeId, onOpen, onEdit }: Props) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead className="hidden sm:table-cell">Address</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="w-0" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {stores.map((s) => (
          <TableRow key={s.id} className={cn(s.id === activeId && "bg-primary/5")}>
            <TableCell className="font-medium">
              {s.name}
              {s.id === activeId && <span className="ml-2 text-xs font-normal text-primary">in context</span>}
            </TableCell>
            <TableCell className="hidden text-muted-foreground sm:table-cell">{s.address ?? "—"}</TableCell>
            <TableCell><StatusPill status={s.status} /></TableCell>
            <TableCell>
              <div className="flex justify-end gap-1">
                <Button variant="ghost" size="sm" onClick={() => onOpen(s)}><ArrowRightLeft /> Open</Button>
                <Button variant="ghost" size="icon-sm" aria-label="Edit" onClick={() => onEdit(s)}><Pencil /></Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
