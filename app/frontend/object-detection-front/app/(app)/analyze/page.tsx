"use client";

import { Loader2, X } from "lucide-react";
import { DetectionViewer } from "@/components/app/detection-viewer";
import { AnalysisResult, LayerToggles } from "@/components/analyze/analysis-result";
import { AnalyzeControls } from "@/components/analyze/analyze-controls";
import { Dropzone } from "@/components/analyze/dropzone";
import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import { useAnalyzer } from "@/hooks/use-analyzer";
import { formatBytes } from "@/lib/format";
import { usePrefs } from "@/stores/prefs-store";

export default function AnalyzePage() {
  const a = useAnalyzer();
  const prefs = usePrefs();

  return (
    <>
      <PageHeader
        title="Analizar imagen"
        description="Sube una foto de la estantería. El modelo marca los productos presentes y los huecos con producto faltante."
        actions={
          a.file && (
            <Button variant="ghost" size="sm" onClick={a.clear}>
              <X /> Quitar imagen
            </Button>
          )
        }
      />

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div>
          {a.preview ? (
            <div className="relative">
              <DetectionViewer
                src={a.preview}
                width={a.size.w}
                height={a.size.h}
                boxes={a.boxes}
                showObjects={prefs.showObjects}
                showMissing={prefs.showMissing}
                showLabels={prefs.showLabels}
              />
              {a.isAnalyzing && (
                <div className="absolute inset-0 grid place-items-center bg-background/50 backdrop-blur-[1px]">
                  <span className="flex items-center gap-2 rounded-md bg-popover px-3 py-2 text-sm shadow">
                    <Loader2 className="size-4 animate-spin" /> Analizando…
                  </span>
                </div>
              )}
            </div>
          ) : (
            <Dropzone onFile={a.pick} />
          )}
          {a.file && (
            <p className="mt-3 text-center text-xs text-muted-foreground">
              {a.file.name} · {formatBytes(a.file.size)}
            </p>
          )}
        </div>

        <aside className="divide-y lg:-mt-1">
          <AnalyzeControls
            canAnalyze={!!a.file}
            isAnalyzing={a.isAnalyzing}
            hasResult={!!a.result}
            cameraId={a.cameraId}
            shelfId={a.shelfId}
            onCamera={a.selectCamera}
            onShelf={a.setShelfId}
            onAnalyze={a.analyze}
          />
          {a.result && <AnalysisResult result={a.result} />}
          {a.result && <LayerToggles />}
        </aside>
      </div>
    </>
  );
}
