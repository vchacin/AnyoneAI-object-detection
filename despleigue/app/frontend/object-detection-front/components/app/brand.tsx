import { cn } from "@/lib/utils";

/** Marca: tres shelves con un gap (el product out of stock). */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={cn("size-6", className)} aria-hidden>
      <rect x="3" y="4" width="4" height="4" rx="1" className="fill-primary" />
      <rect x="9" y="4" width="4" height="4" rx="1" className="fill-primary" />
      <rect x="15" y="4" width="6" height="4" rx="1" className="fill-primary/40" />
      <rect x="3" y="10" width="6" height="4" rx="1" className="fill-primary" />
      <rect
        x="11"
        y="10"
        width="4"
        height="4"
        rx="1"
        className="stroke-gap"
        strokeWidth="1.5"
        strokeDasharray="2 1.6"
      />
      <rect x="17" y="10" width="4" height="4" rx="1" className="fill-primary/40" />
      <rect x="3" y="16" width="4" height="4" rx="1" className="fill-primary/40" />
      <rect x="9" y="16" width="6" height="4" rx="1" className="fill-primary" />
      <rect x="17" y="16" width="4" height="4" rx="1" className="fill-primary" />
    </svg>
  );
}

export function BrandName({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2 font-semibold tracking-tight", className)}>
      <BrandMark />
      ShelfVision
    </span>
  );
}
