import { apiFetch } from "./client";
import type { OrderStatus } from "@/product.config";

export interface OrderLine {
  id: string;
  coffee_bean_id: string;
  name: string | null;
  origin: string | null;
  quantity_kg: number;
  unit_price: number;
  line_total: number;
}

export interface Order {
  id: string;
  status: OrderStatus;
  total_price: number;
  currency: string;
  eta_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  supplier: { id: string; business_name: string | null };
  items: OrderLine[];
  /** Owner view only */
  source_blend_id?: string | null;
  group_id?: string | null;
  /** Supplier view only: who to ship to. Never any blend data. */
  owner?: { business_name: string | null };
}

export interface OrdersPage {
  items: Order[];
  total: number;
  page: number;
  pages: number;
}

export interface OrdersResponse {
  items: Order[];
}

export function getOrders(
  params: { active?: boolean; status?: OrderStatus; page?: number; per_page?: number } = {}
): Promise<OrdersPage> {
  const qs = new URLSearchParams();
  if (params.active !== undefined) qs.set("active", String(params.active));
  if (params.status) qs.set("status", params.status);
  if (params.page) qs.set("page", String(params.page));
  if (params.per_page) qs.set("per_page", String(params.per_page));
  const q = qs.toString();
  return apiFetch<OrdersPage>(`orders${q ? `?${q}` : ""}`);
}

export function getOrder(id: string): Promise<Order> {
  return apiFetch<Order>(`orders/${id}`);
}

/** One order is created per supplier; the response lists all of them. */
export function createOrder(payload: {
  items: { coffee_bean_id: string; quantity_kg: number }[];
  source_blend_id?: string;
  notes?: string;
}): Promise<OrdersResponse> {
  return apiFetch<OrdersResponse>("orders", { method: "POST", body: payload });
}

export function reorderBlend(blendId: string, totalKg: number): Promise<OrdersResponse> {
  return apiFetch<OrdersResponse>(`blends/${blendId}/reorder`, {
    method: "POST",
    body: { total_kg: totalKg },
  });
}

export function updateOrderStatus(
  id: string,
  status: OrderStatus,
  etaDate?: string
): Promise<Order> {
  return apiFetch<Order>(`orders/${id}/status`, {
    method: "PATCH",
    body: { status, ...(etaDate ? { eta_date: etaDate } : {}) },
  });
}

/** Pull a readable message out of an API error body. */
export function errorMessage(err: unknown, fallback: string): string {
  const body = (err as { body?: { error?: unknown } } | null)?.body;
  return typeof body?.error === "string" ? body.error : fallback;
}
