"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type CameraInput, camerasService } from "@/services/cameras.service";
import { qk } from "./keys";

export function useCameras(storeId: string | null) {
  return useQuery({ queryKey: qk.cameras(storeId ?? ""), queryFn: () => camerasService.list(storeId!), enabled: !!storeId });
}

export function useCameraSummary(storeId: string) {
  return useQuery({ queryKey: qk.cameraSummary(storeId), queryFn: () => camerasService.summary(storeId) });
}

export function useCreateCamera(storeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CameraInput) => camerasService.create(storeId, input),
    meta: { success: "Camera creada" },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.cameras(storeId) }),
  });
}

export function useUpdateCamera(storeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Partial<CameraInput & { status: string }>) =>
      camerasService.update(storeId, id, body),
    meta: { success: "Camera actualizada" },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.cameras(storeId) }),
  });
}

export function useRotateCameraToken(storeId: string) {
  return useMutation({
    mutationFn: (id: string) => camerasService.rotateToken(storeId, id),
  });
}
