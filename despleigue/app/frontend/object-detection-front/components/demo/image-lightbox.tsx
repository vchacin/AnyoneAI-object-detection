"use client";

import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

interface ImageLightboxProps {
  src: string;
  alt: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Capa opcional (cajas/zonas) que se dibuja encima de la imagen ampliada. */
  children?: React.ReactNode;
  controls?: React.ReactNode;
}

/**
 * Lightbox para ver una capture en grande: panel oscuro translúcido con blur
 * sobre el fondo de la page. Reutiliza Dialog para conservar Escape, foco
 * y botón de cierre.
 */
export function ImageLightbox({ src, alt, open, onOpenChange, children, controls }: ImageLightboxProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent lang="en" className="border-none bg-black/85 p-2 shadow-none ring-0 backdrop-blur-md sm:max-w-[92vw]">
        <DialogTitle className="sr-only">{alt}</DialogTitle>
        {controls}
        <div className="relative mx-auto inline-block">
          <img
            src={src}
            alt={alt}
            className={`block max-w-[88vw] rounded-md object-contain ${controls ? "max-h-[75vh]" : "max-h-[85vh]"}`}
          />
          {children}
        </div>
      </DialogContent>
    </Dialog>
  );
}
