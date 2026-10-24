import { cn } from "@/lib/utils";

// Plano fijo (sin aleatoriedad) de una estanteria: 0 = hueco, el resto son productos.
const SHELF: number[][] = [
  [3, 2, 4, 2, 3, 0, 2, 4],
  [2, 4, 0, 3, 2, 3, 4, 2],
  [4, 2, 3, 2, 0, 2, 3, 4],
  [2, 3, 2, 4, 3, 2, 0, 3],
];

const TONES = ["bg-primary/70", "bg-primary/35", "bg-muted-foreground/25"];

export function ShelfArt() {
  return (
    <div className="relative hidden flex-1 overflow-hidden border-r bg-sidebar lg:block">
      <div className="absolute inset-0 flex flex-col justify-center gap-10 p-14">
        <div className="space-y-5">
          {SHELF.map((row, r) => (
            <div key={r} className="flex items-end gap-2 border-b-2 border-border pb-1.5">
              {row.map((w, c) =>
                w === 0 ? (
                  <div key={c} className="h-14 w-12 shrink-0 rounded-md border-2 border-dashed border-gap/80 bg-gap/10" />
                ) : (
                  <div key={c} style={{ width: `${w * 14}px` }} className={cn("h-14 shrink-0 rounded-md", TONES[(r + c) % 3])} />
                ),
              )}
            </div>
          ))}
        </div>
        <div className="max-w-md">
          <h2 className="text-2xl font-semibold tracking-tight text-balance">
            Cada hueco en la góndola es una venta que se pierde.
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Analiza fotos de tus estanterías, detecta producto faltante y avisa al equipo antes de que el cliente lo note.
          </p>
        </div>
      </div>
    </div>
  );
}
