import { Check, CheckCheck } from "lucide-react";
import Link from "next/link";
import { AlertStatusPill, SeverityTag } from "@/components/common/badges";
import { Button } from "@/components/ui/button";
import type { Alert, AlertStatus } from "@/lib/api/types";
import { formatFullDate, timeAgo } from "@/lib/format";

interface Props {
  alert: Alert;
  shelfName: string;
  canAck: boolean;
  busy: boolean;
  onTransition: (status: Exclude<AlertStatus, "open">) => void;
}

export function AlertRow({ alert: a, shelfName, canAck, busy, onTransition }: Props) {
  return (
    <li className="flex flex-wrap items-center gap-x-6 gap-y-2 py-3.5">
      <span className="w-16 shrink-0">
        <SeverityTag severity={a.severity} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium">{shelfName}</span>
        <span className="text-xs text-muted-foreground" title={formatFullDate(a.created_at)}>
          Created {timeAgo(a.created_at)}
          {a.acked_at && ` · acknowledged ${timeAgo(a.acked_at)}`}
          {a.closed_at && ` · closed ${timeAgo(a.closed_at)}`}
        </span>
      </span>
      <AlertStatusPill status={a.status} />
      <div className="flex items-center gap-1">
        <Link href={`/inspections?open=${a.inspection_id}`}>
          <Button variant="ghost" size="sm">View image</Button>
        </Link>
        {canAck && a.status === "open" && (
          <Button variant="outline" size="sm" disabled={busy} onClick={() => onTransition("acknowledged")}>
            <Check /> Acknowledge
          </Button>
        )}
        {canAck && a.status !== "closed" && (
          <Button variant="outline" size="sm" disabled={busy} onClick={() => onTransition("closed")}>
            <CheckCheck /> Close
          </Button>
        )}
      </div>
    </li>
  );
}
