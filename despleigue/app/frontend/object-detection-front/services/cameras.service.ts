import { request } from "@/lib/api/client";
import type { Camera, CameraSummary, CameraWithToken } from "@/lib/api/types";

export interface CameraInput {
  name: string;
  location?: string | null;
  shelf_id?: string | null;
}

export const camerasService = {
  list: (storeId: string) => request<Camera[]>(`/stores/${storeId}/cameras`),
  summary: (storeId: string) => request<CameraSummary[]>(`/stores/${storeId}/cameras/summary`),
  create: (storeId: string, json: CameraInput) =>
    request<CameraWithToken>(`/stores/${storeId}/cameras`, { method: "POST", json }),
  update: (storeId: string, id: string, json: Partial<CameraInput & { status: string }>) =>
    request<Camera>(`/stores/${storeId}/cameras/${id}`, { method: "PATCH", json }),
  rotateToken: (storeId: string, id: string) =>
    request<CameraWithToken>(`/stores/${storeId}/cameras/${id}/rotate-token`, { method: "POST" }),
};
