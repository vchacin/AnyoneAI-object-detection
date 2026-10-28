import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  page: number;
  hasNext: boolean;
  onChange: (page: number) => void;
}

export function Pagination({ page, hasNext, onChange }: Props) {
  return (
    <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
      <span>Page {page + 1}</span>
      <div className="flex gap-1">
        <Button variant="outline" size="icon-sm" disabled={page === 0} onClick={() => onChange(page - 1)} aria-label="Previous">
          <ChevronLeft />
        </Button>
        <Button variant="outline" size="icon-sm" disabled={!hasNext} onClick={() => onChange(page + 1)} aria-label="Next">
          <ChevronRight />
        </Button>
      </div>
    </div>
  );
}
