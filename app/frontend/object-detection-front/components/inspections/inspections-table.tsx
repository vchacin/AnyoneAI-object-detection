import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Inspection } from "@/lib/api/types";
import { formatDate, formatMs } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Props {
  rows: Inspection[];
  dimmed?: boolean;
  shelfName: (id: string | null) => string | undefined;
  cameraName: (id: string | null) => string | undefined;
  onSelect: (inspection: Inspection) => void;
}

const dash = <span className="text-muted-foreground">—</span>;

export function InspectionsTable({ rows, dimmed, shelfName, cameraName, onSelect }: Props) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Fecha</TableHead>
          <TableHead>Estante</TableHead>
          <TableHead className="hidden md:table-cell">Cámara</TableHead>
          <TableHead className="hidden sm:table-cell">Origen</TableHead>
          <TableHead className="text-right">Productos</TableHead>
          <TableHead className="text-right">Huecos</TableHead>
          <TableHead className="hidden text-right md:table-cell">Latencia</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody className={cn(dimmed && "opacity-60 transition-opacity")}>
        {rows.map((i) => (
          <TableRow key={i.id} className="cursor-pointer" onClick={() => onSelect(i)}>
            <TableCell className="tnum">{formatDate(i.created_at)}</TableCell>
            <TableCell>{shelfName(i.shelf_id) ?? dash}</TableCell>
            <TableCell className="hidden md:table-cell">{cameraName(i.camera_id) ?? dash}</TableCell>
            <TableCell className="hidden text-muted-foreground sm:table-cell">{i.source === "camera" ? "Cámara" : "Manual"}</TableCell>
            <TableCell className="tnum text-right">{i.n_objects}</TableCell>
            <TableCell className={cn("tnum text-right font-semibold", i.n_missing > 0 ? "text-gap" : "text-muted-foreground")}>
              {i.n_missing}
            </TableCell>
            <TableCell className="tnum hidden text-right text-muted-foreground md:table-cell">{formatMs(i.latency_ms)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
