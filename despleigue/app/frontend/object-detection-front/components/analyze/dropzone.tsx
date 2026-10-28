"use client";

import { ImageUp } from "lucide-react";
import { useRef, useState } from "react";
import { cn } from "@/lib/utils";

export function Dropzone({ onFile }: { onFile: (file: File | undefined) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          onFile(e.dataTransfer.files[0]);
        }}
        className={cn(
          "flex aspect-[16/9] w-full flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed text-muted-foreground transition-colors outline-none hover:border-primary/50 hover:text-foreground focus-visible:border-primary",
          dragging && "border-primary bg-primary/5 text-foreground",
        )}
      >
        <ImageUp className="size-9" />
        <span className="text-sm font-medium text-foreground">Drag an image here or click to browse</span>
        <span className="text-xs">JPG or PNG · you can also paste with Ctrl+V</span>
      </button>
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png"
        className="hidden"
        onChange={(e) => {
          onFile(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
    </>
  );
}
