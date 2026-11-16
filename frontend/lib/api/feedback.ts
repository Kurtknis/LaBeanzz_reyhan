import { apiFetch } from "./client";

export type BrewContext = "espresso" | "filter" | "milk";

export interface FeedbackEntry {
  id: string;
  blend_id: string;
  owner_id: string;
  overall: number;
  flavor: number;
  body: number;
  acidity: number;
  sweetness: number;
  brew_context: BrewContext;
  comment: string | null;
  recipe_snapshot: { coffee_bean_id: string; percentage: number }[] | null;
  created_at: string;
}

export interface FeedbackListResponse {
  items: FeedbackEntry[];
}

export interface SubmitFeedbackPayload {
  overall: number;
  flavor: number;
  body: number;
  acidity: number;
  sweetness: number;
  brew_context: BrewContext;
  comment?: string;
}

export function getFeedback(blendId: string): Promise<FeedbackListResponse> {
  return apiFetch<FeedbackListResponse>(`blends/${blendId}/feedback`);
}

export function submitFeedback(
  blendId: string,
  payload: SubmitFeedbackPayload
): Promise<FeedbackEntry> {
  return apiFetch<FeedbackEntry>(`blends/${blendId}/feedback`, {
    method: "POST",
    body: payload,
  });
}
