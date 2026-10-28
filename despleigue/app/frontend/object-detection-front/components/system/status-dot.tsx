import { cn } from "@/lib/utils";

export function StatusDot({ ok }: { ok: boolean }) {
  return <span className={cn("mr-2 inline-block size-2 rounded-full", ok ? "bg-ok" : "bg-destructive")} />;
}
