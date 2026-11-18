import { apiFetch } from "./client";

export interface ReorderItem {
  blend_id: string;
  blend_name: string;
  daily_usage_kg: number;
  days_remaining: number;
  limiting_bean: { id: string; name: string };
  reorder_soon: boolean;
}

export interface Spotlight {
  bean: {
    id: string;
    name: string;
    origin: string;
    region: string | null;
    producer: string | null;
    farm: string | null;
    producer_story: string;
  };
  supplier: { id: string; business_name: string | null };
}

export interface DashboardSummary {
  active_orders: number;
  active_blends: number;
  month: string;
  month_kg: number;
  month_spend: number;
  currency: string;
  reorder: ReorderItem[];
  spotlight: Spotlight | null;
}

export interface SpendResponse {
  currency: string;
  items: { month: string; amount: number }[];
}

export interface VolumeResponse {
  items: { month: string; kg: number }[];
}

export interface ReorderResponse {
  threshold_days: number;
  items: ReorderItem[];
}

export interface StockRow {
  coffee_bean_id: string;
  name: string | null;
  origin: string | null;
  quantity_kg: number;
  updated_at: string;
}

export const getDashboardSummary = () => apiFetch<DashboardSummary>("dashboard/summary");
export const getSpend = (months = 6) => apiFetch<SpendResponse>(`insights/spend?months=${months}`);
export const getVolume = (months = 6) => apiFetch<VolumeResponse>(`insights/volume?months=${months}`);
export const getReorder = () => apiFetch<ReorderResponse>("insights/reorder");
export const getOwnerStock = () => apiFetch<{ items: StockRow[] }>("owner-stock");
export const setOwnerStock = (coffeeBeanId: string, quantityKg: number) =>
  apiFetch<StockRow>("owner-stock", {
    method: "PATCH",
    body: { coffee_bean_id: coffeeBeanId, quantity_kg: quantityKg },
  });
