import { apiFetch } from "./client";

// ─── Request / Response types ─────────────────────────────────────────────────

export type BlendStyle = "espresso" | "filter" | "milk";

export interface GenerateBlendRequest {
  prompt: string;
  style?: BlendStyle;
  preset_id?: string | null;
  max_price_per_kg?: number | null;
}

export interface RecipeItem {
  coffee_bean_id: string;
  name: string;
  origin: string;
  percentage: number;
}

export interface BlendProfile {
  computed: {
    acidity: number;
    body: number;
    sweetness: number;
  };
  estimated: {
    chocolate: number;
    caramel: number;
    fruitiness: number;
    nuttiness: number;
    florality: number;
  };
}

export interface BlendDraft {
  blend_name: string;
  description: string;
  recipe: RecipeItem[];
  profile: BlendProfile;
  reasoning: string;
  applied_feedback: string[];
}

export interface GenerateBlendResponse {
  generation_id: string;
  draft: BlendDraft;
}

export interface AIGeneration {
  id: string;
  owner_id: string;
  kind: string;
  input: Record<string, unknown>;
  validated_output: BlendDraft | null;
  status: "OK" | "INVALID" | "ERROR";
  model: string | null;
  latency_ms: number | null;
  error: string | null;
  created_at: string;
}

// ─── API calls ────────────────────────────────────────────────────────────────

export async function generateBlend(
  body: GenerateBlendRequest
): Promise<GenerateBlendResponse> {
  return apiFetch<GenerateBlendResponse>("ai/generate-blend", {
    method: "POST",
    body,
  });
}

export async function getGeneration(id: string): Promise<AIGeneration> {
  return apiFetch<AIGeneration>(`ai/generations/${id}`);
}

/** Propose a re-balanced recipe for a blend whose beans ran out. Saves nothing. */
export async function substituteBean(body: {
  blend_id: string;
  missing_bean_id?: string;
}): Promise<GenerateBlendResponse> {
  return apiFetch<GenerateBlendResponse>("ai/substitute", { method: "POST", body });
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export async function sendChat(messages: ChatMessage[]): Promise<{ generation_id: string; reply: string }> {
  return apiFetch("ai/chat", { method: "POST", body: { messages } });
}

export interface FeedbackAnalysis {
  generation_id: string;
  summary: string;
  patterns: string[];
  stats: Record<
    string,
    { count: number; overall: number; flavor: number; body: number; acidity: number; sweetness: number }
  >;
  taste_adjustments: Record<string, Record<string, number>>;
}

export async function analyzeFeedback(): Promise<FeedbackAnalysis> {
  return apiFetch<FeedbackAnalysis>("ai/analyze-feedback", { method: "POST" });
}
