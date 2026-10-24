import { ArrowRight } from "lucide-react";
import Link from "next/link";

export function SectionLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
      {children} <ArrowRight className="size-3" />
    </Link>
  );
}
