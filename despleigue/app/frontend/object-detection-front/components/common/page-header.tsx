import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-x-6 gap-y-3 pb-6", className)}>
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/** Inline metrics separated by dividers (no cards). */
export function StatStrip({
  items,
  className,
}: {
  items: { label: string; value: React.ReactNode; hint?: string; tone?: "default" | "gap" | "ok" }[];
  className?: string;
}) {
  return (
    <dl className={cn("grid grid-cols-2 border-y sm:flex sm:divide-x", className)}>
      {items.map((it, i) => (
        <div
          key={it.label}
          className={cn(
            "flex-1 py-4 sm:px-6 sm:first:pl-0",
            i % 2 === 1 && "pl-4",
            i >= 2 && "border-t sm:border-t-0",
          )}
        >
          <dt className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{it.label}</dt>
          <dd
            className={cn(
              "tnum mt-1 text-2xl font-semibold tracking-tight",
              it.tone === "gap" && "text-gap",
              it.tone === "ok" && "text-ok",
            )}
          >
            {it.value}
          </dd>
          {it.hint && <p className="mt-0.5 text-xs text-muted-foreground">{it.hint}</p>}
        </div>
      ))}
    </dl>
  );
}

/** Section title used to separate blocks without enclosing them in cards. */
export function Section({
  title,
  description,
  actions,
  children,
  className,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("py-6", className)}>
      <div className="mb-3 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold">{title}</h2>
          {description && <p className="text-xs text-muted-foreground">{description}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}
