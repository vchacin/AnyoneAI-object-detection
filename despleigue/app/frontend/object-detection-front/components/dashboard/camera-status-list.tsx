import { ActivePill } from "@/components/common/badges";
import type { CameraSummary } from "@/lib/api/types";
import { timeAgo } from "@/lib/format";
import { MissingCount } from "./recent-inspections";

export function CameraStatusList({ cameras }: { cameras: CameraSummary[] }) {
  return (
    <ul className="divide-y">
      {cameras.map((c) => (
        <li key={c.id} className="flex items-center gap-3 py-2.5 text-sm">
          <span className="min-w-0 flex-1">
            <span className="block truncate font-medium">{c.alias}</span>
            <span className="text-xs text-muted-foreground">Visto {timeAgo(c.last_seen)}</span>
          </span>
          <ActivePill active={c.status === "active"} />
          <span className="w-14 text-right">
            <MissingCount n={c.n_missing} />
            <span className="text-xs text-muted-foreground"> gaps</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
