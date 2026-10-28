import { Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Shelf } from "@/lib/api/types";

interface Props {
  shelves: Shelf[];
  canManage: boolean;
  onEdit: (shelf: Shelf) => void;
}

export function ShelvesTable({ shelves, canManage, onEdit }: Props) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Zone</TableHead>
          <TableHead className="text-right">Allowed gaps</TableHead>
          <TableHead className="w-0" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {shelves.map((s) => (
          <TableRow key={s.id}>
            <TableCell className="font-medium">{s.name}</TableCell>
            <TableCell className="text-muted-foreground">{s.zone ?? "—"}</TableCell>
            <TableCell className="tnum text-right">{s.gap_threshold}</TableCell>
            <TableCell>
              {canManage && (
                <div className="flex justify-end">
                  <Button variant="ghost" size="icon-sm" aria-label="Edit" onClick={() => onEdit(s)}><Pencil /></Button>
                </div>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
