import { ScanSearch } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import type { Inspection } from "@/lib/api/types";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

export function MissingCount({ n }: { n: number }) {
  return <span className={cn("tnum font-semibold", n > 0 ? "text-gap" : "text-muted-foreground")}>{n}</span>;
}

interface Props {
  rows: Inspection[];
  /** Texto principal de cada fila (estante o tienda). */
  labelFor: (inspection: Inspection) => string;
}

export function RecentInspections({ rows, labelFor }: Props) {
  if (!rows.length) {
    return (
      <EmptyState
        icon={ScanSearch}
        title="Aún no hay inspecciones"
        description="Analiza una imagen o conecta una cámara para empezar."
        action={
          <Link href="/analyze">
            <Button size="sm">Analizar imagen</Button>
          </Link>
        }
      />
    );
  }
  return (
    <ul className="divide-y">
      {rows.map((i) => (
        <li key={i.id}>
          <Link
            href={`/inspections?open=${i.id}`}
            className="-mx-2 flex items-center gap-4 rounded-md px-2 py-2.5 text-sm transition-colors hover:bg-muted/60"
          >
            <span className="tnum w-24 shrink-0 text-muted-foreground">{formatDate(i.created_at)}</span>
            <span className="min-w-0 flex-1 truncate">{labelFor(i)}</span>
            <span className="hidden w-20 text-right text-xs text-muted-foreground sm:block">
              {i.source === "camera" ? "Cámara" : "Manual"}
            </span>
            <span className="tnum w-16 text-right text-muted-foreground">{i.n_objects} prod.</span>
            <span className="w-16 text-right">
              <MissingCount n={i.n_missing} /> <span className="text-xs text-muted-foreground">huecos</span>
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
