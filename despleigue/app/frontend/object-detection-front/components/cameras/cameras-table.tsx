import { KeyRound, Pencil } from "lucide-react";
import { StatusPill } from "@/components/common/badges";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Camera } from "@/lib/api/types";
import { timeAgo } from "@/lib/format";

interface Props {
  cameras: Camera[];
  shelfName: (id: string | null) => string | undefined;
  canManage: boolean;
  onEdit: (camera: Camera) => void;
  onRotate: (camera: Camera) => void;
}

export function CamerasTable({ cameras, shelfName, canManage, onEdit, onRotate }: Props) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead className="hidden sm:table-cell">Location</TableHead>
          <TableHead>Shelf</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="hidden md:table-cell">Last seen</TableHead>
          <TableHead className="w-0" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {cameras.map((c) => (
          <TableRow key={c.id}>
            <TableCell className="font-medium">{c.name}</TableCell>
            <TableCell className="hidden text-muted-foreground sm:table-cell">{c.location ?? "—"}</TableCell>
            <TableCell>{shelfName(c.shelf_id) ?? <span className="text-muted-foreground">—</span>}</TableCell>
            <TableCell><StatusPill status={c.status} /></TableCell>
            <TableCell className="hidden text-muted-foreground md:table-cell">{timeAgo(c.last_seen)}</TableCell>
            <TableCell>
              {canManage && (
                <div className="flex justify-end gap-1">
                  <Button variant="ghost" size="icon-sm" aria-label="Edit" onClick={() => onEdit(c)}><Pencil /></Button>
                  <Button variant="ghost" size="icon-sm" aria-label="Rotar token" onClick={() => onRotate(c)}><KeyRound /></Button>
                </div>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
