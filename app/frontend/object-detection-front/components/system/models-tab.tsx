"use client";

import { EmptyState, RowsSkeleton } from "@/components/common/states";
import { QueryBoundary } from "@/components/common/query-boundary";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useModels } from "@/hooks/queries/use-system";
import { pct } from "@/lib/format";
import { StatusDot } from "./status-dot";

export function ModelsTab() {
  const models = useModels();
  return (
    <QueryBoundary
      query={models}
      skeleton={<RowsSkeleton />}
      isEmpty={(c) => !c.models.length}
      empty={<EmptyState title="Sin modelos registrados" />}
    >
      {(catalog) => (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Modelo</TableHead>
              <TableHead>Pipeline</TableHead>
              <TableHead className="hidden sm:table-cell">Versión</TableHead>
              <TableHead className="text-right">imgsz</TableHead>
              <TableHead className="text-right">Conf.</TableHead>
              <TableHead>Estado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {catalog.models.map((m) => (
              <TableRow key={m.name}>
                <TableCell className="font-medium">
                  {m.name}
                  {m.name === catalog.default_model && <span className="ml-2 text-xs font-normal text-primary">activo</span>}
                  <span className="block font-mono text-xs font-normal text-muted-foreground">{m.sha256}</span>
                </TableCell>
                <TableCell className="text-muted-foreground">{m.pipeline}</TableCell>
                <TableCell className="hidden text-muted-foreground sm:table-cell">{m.version}</TableCell>
                <TableCell className="tnum text-right">{m.imgsz}</TableCell>
                <TableCell className="tnum text-right">{pct(m.default_conf)}</TableCell>
                <TableCell><StatusDot ok={m.available} />{m.available ? "Disponible" : "Sin pesos"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </QueryBoundary>
  );
}
