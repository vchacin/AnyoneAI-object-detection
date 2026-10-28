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
      empty={<EmptyState title="No models registered" />}
    >
      {(catalog) => (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Model</TableHead>
              <TableHead>Pipeline</TableHead>
              <TableHead className="hidden sm:table-cell">Version</TableHead>
              <TableHead className="text-right">imgsz</TableHead>
              <TableHead className="text-right">Conf.</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {catalog.models.map((m) => (
              <TableRow key={m.name}>
                <TableCell className="font-medium">
                  {m.name}
                  {m.name === catalog.default_model && <span className="ml-2 text-xs font-normal text-primary">active</span>}
                  <span className="block font-mono text-xs font-normal text-muted-foreground">{m.sha256}</span>
                </TableCell>
                <TableCell className="text-muted-foreground">{m.pipeline}</TableCell>
                <TableCell className="hidden text-muted-foreground sm:table-cell">{m.version}</TableCell>
                <TableCell className="tnum text-right">{m.imgsz}</TableCell>
                <TableCell className="tnum text-right">{pct(m.default_conf)}</TableCell>
                <TableCell><StatusDot ok={m.available} />{m.available ? "Available" : "No weights"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </QueryBoundary>
  );
}
