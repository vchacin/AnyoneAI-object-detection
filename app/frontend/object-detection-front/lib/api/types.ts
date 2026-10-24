// Tipos derivados del backend (docs/api.json no tipa las respuestas, asi que
// salen de los routers de app/backend).

export type Role = "super_admin" | "store_admin" | "employee" | "viewer";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface User {
  id: string;
  email: string;
  role: Role;
  store_id: string | null;
  is_active: boolean;
}

export interface Store {
  id: string;
  name: string;
  address: string | null;
  status: "active" | "inactive" | string;
}

export interface StoreSettings {
  store_id: string;
  timezone: string;
  opening_time: string | null;
  closing_time: string | null;
  peak_hours: unknown[] | null;
  default_conf: number;
  alert_cooldown_minutes: number;
}

export interface Camera {
  id: string;
  store_id: string;
  shelf_id: string | null;
  name: string;
  location: string | null;
  status: "active" | "inactive" | string;
  last_seen: string | null;
}

export interface CameraWithToken extends Camera {
  token: string;
}

export interface Shelf {
  id: string;
  store_id: string;
  name: string;
  zone: string | null;
  gap_threshold: number;
}

export interface StoreUser {
  id: string;
  store_id: string | null;
  email: string;
  role: Role;
  is_active: boolean;
}

export interface Employee {
  id: string;
  store_id: string;
  user_id: string | null;
  full_name: string;
  position: string | null;
  is_active: boolean;
}

export interface Shift {
  id: string;
  store_id: string;
  employee_id: string;
  weekday: number;
  start_time: string;
  end_time: string;
}

export interface InspectionDetection {
  class: string;
  bbox: [number, number, number, number];
  confidence: number;
  source: string | null;
}

export interface Inspection {
  id: string;
  store_id: string;
  camera_id: string | null;
  shelf_id: string | null;
  image_key: string | null;
  image_width: number | null;
  image_height: number | null;
  image_bytes: number | null;
  source: "manual" | "camera" | string;
  model_version: string;
  n_objects: number;
  n_missing: number;
  latency_ms: number | null;
  created_by: string | null;
  employee_id: string | null;
  created_at: string | null;
  detections: InspectionDetection[];
}

export type AlertStatus = "open" | "acknowledged" | "closed";
export type AlertSeverity = "low" | "medium" | "high";

export interface Alert {
  id: string;
  store_id: string;
  inspection_id: string;
  shelf_id: string | null;
  severity: AlertSeverity;
  status: AlertStatus;
  acked_by: string | null;
  created_at: string;
  acked_at: string | null;
  closed_at: string | null;
}

export interface StoreDashboard {
  store_id: string;
  open_alerts_count: number;
  inspections_today: number;
  latest_inspections: Inspection[];
  latest_by_shelf: { shelf_id: string; name: string; n_missing: number }[];
}

export interface GlobalDashboard {
  active_stores: number;
  monthly_images_processed: number;
  recent_inspections: Inspection[];
}

export interface CameraSummary {
  id: string;
  alias: string;
  status: string;
  last_seen: string | null;
  last_inspection_id: string | null;
  n_objects: number;
  n_missing: number;
}

export interface UsageMetrics {
  store_id: string | null;
  images_processed: number;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  estimated_cost_per_1000: number | null;
}

export interface Health {
  status: string;
  model_loaded: boolean;
  auth_required: boolean;
  database: string;
  model_version: string | null;
  model_sha256: string | null;
  device: string | null;
  imgsz: number | null;
}

export interface ModelInfo {
  name: string;
  version: string;
  pipeline: string;
  imgsz: number;
  max_det: number;
  default_conf: number;
  classes: string[];
  sha256: string;
  source: string;
  available: boolean;
}

export interface ModelCatalog {
  default_model: string;
  models: ModelInfo[];
}

export interface DetectionBox {
  box: [number, number, number, number];
  confidence: number;
  class: string;
  source?: string | null;
  confidence_type?: string;
}

export interface ConfidenceStats {
  count: number;
  min: number | null;
  median: number | null;
  max: number | null;
  types?: string[];
}

export interface PredictResponse {
  inspection_id: string | null;
  image_name: string;
  width: number;
  height: number;
  n_objects: number;
  n_missing: number;
  objects: DetectionBox[];
  candidates: DetectionBox[];
  missing: DetectionBox[];
  conf: number;
  confidence_threshold: number;
  confidence_summary: {
    objects: ConfidenceStats;
    missing: ConfidenceStats;
    all: { count: number };
  };
  auto_score: number;
  used_coco: boolean;
  model_name: string;
  model_version: string;
  timings: Record<string, number>;
  detections: DetectionBox[];
  camera_id: string | null;
  shelf_id: string | null;
  gap_mode: string | null;
  latency_ms: number | null;
  experiment_id: string | null;
  experiment_report: string | null;
  detection_id: number | null;
}

export interface ComparisonRun {
  run_id: string;
  created_at: string;
  processed_count: number;
  seed: number | null;
}

export interface ComparisonEntry {
  index: number;
  image_name: string;
  official_image: string;
  shelfvision_image: string;
  official: Record<string, unknown>;
  shelfvision: Record<string, unknown>;
}

export interface ComparisonManifest {
  run_id: string;
  entries: ComparisonEntry[];
  [key: string]: unknown;
}

export type Verdict = "official" | "shelfvision" | "tie" | "unclear";
