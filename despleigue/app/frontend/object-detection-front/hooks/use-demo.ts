"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { demoService, type BackendProvider, type CaptureSlot, type DemoAnalysisResult } from "@/services/demo.service";
import { ApiError } from "@/lib/api/client";

export const DEMO_SLOTS: CaptureSlot[] = [
  { id: "08", time: "08:00" },
  { id: "10", time: "10:00" },
  { id: "12", time: "12:00" },
  { id: "14", time: "14:00" },
  { id: "16", time: "16:00" },
  { id: "18", time: "18:00" },
];
const LAMBDA_IMAGE_SIZES = [640, 960, 1280, 1600, 1920];

export interface DemoMetrics {
  captures: number;
  observedHours: string;
  estado: string;
}

export function useDemo() {
  const [provider, setProvider] = useState<BackendProvider>("local");
  const [confidence, setConfidence] = useState(0.19);
  const [iou, setIou] = useState(0.7);
  const [sahi, setSahi] = useState(false);
  const [imageSize, setImageSize] = useState(640);
  const [settingsBusy, setSettingsBusy] = useState(true);
  const [settingsMessage, setSettingsMessage] = useState("");
  const selectProvider = useCallback((next: BackendProvider) => {
    setProvider(next);
    if (next === "lambda" && !LAMBDA_IMAGE_SIZES.includes(imageSize)) setImageSize(640);
  }, [imageSize]);

  useEffect(() => {
    let cancelled = false;
    demoService.loadSettings().then((profile) => {
      if (cancelled) return;
      setProvider(profile.provider);
      setConfidence(profile.confidence);
      setIou(profile.iou);
      setSahi(profile.sahi);
      setImageSize(profile.provider === "lambda" && !LAMBDA_IMAGE_SIZES.includes(profile.imageSize)
        ? 640 : profile.imageSize);
      setSettingsMessage("Shared settings loaded from the backend.");
    }).catch(() => {
      if (!cancelled) setSettingsMessage("Could not load shared settings. Defaults are shown; changes are not saved.");
    }).finally(() => { if (!cancelled) setSettingsBusy(false); });
    return () => { cancelled = true; };
  }, []);

  const saveSettings = useCallback(async () => {
    setSettingsBusy(true);
    try {
      await demoService.saveSettings({ version: 1, provider, confidence, iou, sahi, imageSize });
      setSettingsMessage("Settings saved on the backend and shared across browsers.");
    } catch {
      setSettingsMessage("Could not save settings. Check your connection and administrator permissions.");
    } finally {
      setSettingsBusy(false);
    }
  }, [provider, confidence, iou, sahi, imageSize]);
  const [captures, setCaptures] = useState<Record<string, File | null>>(
    Object.fromEntries(DEMO_SLOTS.map((s) => [s.id, null])),
  );
  const [previews, setPreviews] = useState<Record<string, string | null>>(
    Object.fromEntries(DEMO_SLOTS.map((s) => [s.id, null])),
  );
  const [results, setResults] = useState<Record<string, DemoAnalysisResult>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [analyzing, setAnalyzing] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);

  const uploadedCount = useMemo(
    () => DEMO_SLOTS.filter((s) => previews[s.id]).length,
    [previews],
  );

  const metrics: DemoMetrics = useMemo(() => {
    const analyzed = DEMO_SLOTS.filter((s) => results[s.id]);
    const missingSlots = analyzed.filter((s) => results[s.id].nMissing > 0).length;
    return {
      captures: analyzed.length,
      observedHours: analyzed.length ? `${analyzed[0].time} – ${analyzed[analyzed.length - 1].time}` : "No analysis",
      estado: !analyzed.length ? "Analysis pending" : missingSlots ? "Gaps detected" : "No gaps detected",
    };
  }, [results]);

  const setCapture = useCallback((slotId: string, file: File | null) => {
    setCaptures((prev) => ({ ...prev, [slotId]: file }));
    setErrors((prev) => { const next = { ...prev }; delete next[slotId]; return next; });
    setResults((prev) => {
      if (!(slotId in prev)) return prev;
      const next = { ...prev };
      delete next[slotId];
      return next;
    });
    setPreviews((prev) => {
      const old = prev[slotId];
      if (old) URL.revokeObjectURL(old);
      return { ...prev, [slotId]: file ? URL.createObjectURL(file) : null };
    });
  }, []);

  /**
   * Carga automática de las 6 captures de muestra (public/demo/1.png…6.png),
   * mapeadas a los schedules 08:00→18:00. Evita subir archivos a mano en el pitch.
   */
  const loadSamples = useCallback(async () => {
    for (let i = 0; i < DEMO_SLOTS.length; i += 1) {
      const res = await fetch(`/demo/${i + 1}.png`);
      if (!res.ok) throw new Error(`Could not load /demo/${i + 1}.png`);
      const blob = await res.blob();
      setCapture(DEMO_SLOTS[i]!.id, new File([blob], `${i + 1}.png`, { type: "image/png" }));
    }
  }, [setCapture]);

  /** Analyze las captures subidas y conserva los fallos como pendientes. */
  const runAnalysis = useCallback(async () => {
    const pending = DEMO_SLOTS.filter((s) => captures[s.id]);
    if (!pending.length) return;
    setAnalyzing(true);
    try {
      const next: Record<string, DemoAnalysisResult> = {};
      const failures: Record<string, string> = {};
      for (const slot of pending) {
        try {
          const r = await demoService.analyze(captures[slot.id]!, provider, confidence, iou, sahi, imageSize);
          next[slot.id] = { ...r, slotId: slot.id };
        } catch (error) {
          if (error instanceof ApiError) {
            const messages: Record<number, string> = {
              0: "Could not connect to the backend.",
              401: "Your session has expired. Please sign in again.",
              413: "The image is too large for the selected backend.",
              422: "The image or analysis settings were rejected.",
              502: "The remote inference service could not complete the analysis.",
              503: "The inference service is unavailable or not configured.",
            };
            failures[slot.id] = messages[error.status] ?? `Analysis failed (HTTP ${error.status}).`;
          } else {
            failures[slot.id] = error instanceof Error ? error.message : "Could not analyze the image";
          }
        }
      }
      setResults(next);
      setErrors(failures);
    } finally {
      setAnalyzing(false);
    }
  }, [captures, provider, confidence, iou, sahi, imageSize]);

  const generateReport = useCallback(() => setReportOpen(true), []);

  return {
    provider,
    setProvider: selectProvider,
    settingsBusy,
    settingsMessage,
    saveSettings,
    confidence,
    setConfidence,
    iou,
    setIou,
    sahi,
    setSahi,
    imageSize,
    setImageSize,
    captures,
    previews,
    setCapture,
    loadSamples,
    results,
    errors,
    uploadedCount,
    analyzing,
    runAnalysis,
    reportOpen,
    setReportOpen,
    generateReport,
    metrics,
  };
}
