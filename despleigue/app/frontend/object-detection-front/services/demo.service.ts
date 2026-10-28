import { request } from "@/lib/api/client";

export type BackendProvider = "local" | "lambda" | "runpod";

export interface DemoInferenceSettings {
  version: 1;
  provider: BackendProvider;
  confidence: number;
  iou: number;
  sahi: boolean;
  imageSize: number;
}

export interface CaptureSlot {
  id: string;
  time: string;
}

/** Caja en píxeles de la imagen analizada. */
export interface DemoBox {
  box: [number, number, number, number];
  class: string;
  confidence?: number | null;
  source?: string;
}

/** Resultado normalizado de POST /inference (la API responde snake_case). */
export interface DemoAnalysisResult {
  slotId: string;
  width: number;
  height: number;
  nObjects: number;
  nMissing: number;
  objects: DemoBox[];
  missing: DemoBox[];
  detections: DemoBox[];
  confidenceThreshold: number;
  iouThreshold: number | null;
  provider: BackendProvider;
  sahi: boolean;
  imageSize: number | null;
}

type RawInference = Omit<DemoAnalysisResult, "slotId" | "nObjects" | "nMissing" | "confidenceThreshold" | "iouThreshold" | "provider" | "sahi" | "imageSize"> & {
  n_objects: number;
  n_missing: number;
  confidence_threshold: number;
  iou?: number | null;
  sahi?: boolean;
  imgsz?: number | null;
};

export const demoService = {
  loadSettings: () => request<DemoInferenceSettings>("/demo/settings"),
  saveSettings: (settings: DemoInferenceSettings) => request<DemoInferenceSettings>("/demo/settings", { method: "PUT", json: settings }),
  /**
   * Envía una imagen al backend de inferencia usando el proveedor elegido.
   * Por defecto el backend está desplegado en AWS Lambda; RunPod se habilita
   * cambiando el proveedor en la UI.
   */
  analyze: async (file: File, provider: BackendProvider, confidence: number, iou: number, sahi: boolean, imageSize: number) => {
    const body = new FormData();
    body.append("image", file);
    body.append("provider", provider);
    body.append("conf", String(confidence));
    if (provider === "local" || provider === "lambda") {
      body.append("iou", String(iou));
      body.append("imgsz", String(imageSize));
    }
    if (provider === "local") body.append("sahi", String(sahi));
    // persist=false porque en demo no queremos guardar inspections de prueba.
    const raw = await request<RawInference>("/inference", {
      method: "POST",
      query: { persist: false, demo: true },
      body,
    });
    const objects = raw.objects ?? [];
    const missing = raw.missing ?? [];
    if ((provider === "local" || provider === "lambda") && (typeof raw.iou !== "number" || Math.abs(raw.iou - iou) > 1e-6)) {
      throw new Error("The inference service did not confirm the requested IoU. Analyze again.");
    }
    if (provider === "local" && sahi && raw.sahi !== true) {
      throw new Error("The backend did not confirm SAHI. Restart the backend and analyze again.");
    }
    if ((provider === "local" || provider === "lambda") && raw.imgsz !== imageSize) {
      throw new Error("The inference service did not confirm the requested size. Analyze again.");
    }
    return {
      width: raw.width,
      height: raw.height,
      nObjects: raw.n_objects ?? objects.length,
      nMissing: raw.n_missing ?? missing.length,
      objects,
      missing,
      detections: [...objects, ...missing],
      confidenceThreshold: raw.confidence_threshold,
      iouThreshold: raw.iou ?? null,
      provider,
      sahi: raw.sahi === true,
      imageSize: raw.imgsz ?? null,
    };
  },
};
