import { apiFetch } from "./client";
import type { BlendStatus, BlendStyle } from "@/product.config";

export interface BlendItem {
  id: string;
  blend_id: string;
  coffee_bean_id: string;
  percentage: number;
  bean: {
    id: string;
    name: string;
    origin: string;
    roast_level: string;
    acidity: number;
    body: number;
    sweetness: number;
    price_per_kg: number;
    status: string;
  } | null;
}

export interface Blend {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  status: BlendStatus;
  source_generation_id: string | null;
  predicted_profile: {
    computed: { acidity: number; body: number; sweetness: number };
  } | null;
  daily_usage_kg: number | null;
  style: BlendStyle | null;
  version: number;
  items: BlendItem[];
  created_at: string;
  updated_at: string;
}

export interface BlendsPage {
  items: Blend[];
  total: number;
  page: number;
  pages: number;
}

export interface CreateBlendPayload {
  name: string;
  description?: string;
  style?: BlendStyle;
  items: { coffee_bean_id: string; percentage: number }[];
  source_generation_id?: string | null;
}

export interface PatchBlendPayload {
  name?: string;
  description?: string;
  style?: BlendStyle;
  items?: { coffee_bean_id: string; percentage: number }[];
}

export interface SetStatusPayload {
  status: BlendStatus;
  daily_usage_kg?: number;
}

export function getBlends(params: { status?: BlendStatus; page?: number; per_page?: number } = {}): Promise<BlendsPage> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.page) qs.set("page", String(params.page));
  if (params.per_page) qs.set("per_page", String(params.per_page));
  const q = qs.toString();
  return apiFetch<BlendsPage>(`blends${q ? `?${q}` : ""}`);
}

export function getBlend(id: string): Promise<Blend> {
  return apiFetch<Blend>(`blends/${id}`);
}

export function createBlend(payload: CreateBlendPayload): Promise<Blend> {
  return apiFetch<Blend>("blends", { method: "POST", body: payload });
}

export function patchBlend(id: string, payload: PatchBlendPayload): Promise<Blend> {
  return apiFetch<Blend>(`blends/${id}`, { method: "PATCH", body: payload });
}

export function setBlendStatus(id: string, payload: SetStatusPayload): Promise<Blend> {
  return apiFetch<Blend>(`blends/${id}/status`, { method: "POST", body: payload });
}

export function duplicateBlend(id: string): Promise<Blend> {
  return apiFetch<Blend>(`blends/${id}/duplicate`, { method: "POST" });
}
