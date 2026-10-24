import { Switch } from "@/components/ui/switch";

export function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center justify-between py-1.5 text-sm">
      {label}
      <Switch size="sm" checked={checked} onCheckedChange={onChange} />
    </label>
  );
}
