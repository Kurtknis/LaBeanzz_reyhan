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
