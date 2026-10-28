"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { BackendProvider } from "@/services/demo.service";

interface DemoBackendSelectorProps {
  value: BackendProvider;
  onChange: (value: BackendProvider) => void;
  disabled?: boolean;
}

export function DemoBackendSelector({ value, onChange, disabled }: DemoBackendSelectorProps) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-muted-foreground">Inference backend</span>
      <Select value={value} disabled={disabled} onValueChange={(v) => onChange(v as BackendProvider)}>
        <SelectTrigger className="w-40">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="local">Local model</SelectItem>
          <SelectItem value="lambda">AWS Lambda</SelectItem>
          <SelectItem value="runpod">RunPod</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
