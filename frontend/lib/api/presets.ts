import { apiFetch } from "./client";
import type { BlendStyle } from "@/product.config";

export interface Preset {
  id: string;
  owner_id: string;
  name: string;
  flavor_preferences: Record<string, unknown>;
  acidity_pref: number | null;
  body_pref: number | null;
  sweetness_pref: number | null;
  brewing_method: string | null;
  coffee_style: BlendStyle | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PresetsResponse {
  items: Preset[];
}

export interface CreatePresetPayload {
  name: string;
  flavor_preferences?: Record<string, unknown>;
  acidity_pref?: number | null;
  body_pref?: number | null;
  sweetness_pref?: number | null;
  brewing_method?: string | null;
  coffee_style?: BlendStyle | null;
  notes?: string | null;
}

export type PatchPresetPayload = Partial<CreatePresetPayload>;

export function getPresets(): Promise<PresetsResponse> {
  return apiFetch<PresetsResponse>("presets");
}

export function createPreset(payload: CreatePresetPayload): Promise<Preset> {
  return apiFetch<Preset>("presets", { method: "POST", body: payload });
}

export function patchPreset(id: string, payload: PatchPresetPayload): Promise<Preset> {
  return apiFetch<Preset>(`presets/${id}`, { method: "PATCH", body: payload });
}

export function deletePreset(id: string): Promise<void> {
  return apiFetch<void>(`presets/${id}`, { method: "DELETE" });
}
