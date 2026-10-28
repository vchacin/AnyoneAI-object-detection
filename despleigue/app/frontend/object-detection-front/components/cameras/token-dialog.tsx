"use client";

import { Copy } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface Props {
  token: { value: string; camera: string } | null;
  onClose: () => void;
}

export function TokenDialog({ token, onClose }: Props) {
  return (
    <Dialog open={!!token} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Token for “{token?.camera}”</DialogTitle>
          <DialogDescription>
            Copy it now; it will not be shown again. The camera sends it in the header{" "}
            <code className="font-mono">X-Camera-Token</code> at <code className="font-mono">/inference</code>.
          </DialogDescription>
        </DialogHeader>
        <div className="flex items-center gap-2 rounded-md bg-muted p-2">
          <code className="min-w-0 flex-1 font-mono text-xs break-all">{token?.value}</code>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Copy token"
            onClick={() => {
              void navigator.clipboard.writeText(token?.value ?? "");
              toast.success("Token copied");
            }}
          >
            <Copy />
          </Button>
        </div>
        <DialogFooter>
          <Button onClick={onClose}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
