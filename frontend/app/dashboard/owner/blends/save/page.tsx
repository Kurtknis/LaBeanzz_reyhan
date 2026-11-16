"use client";

import { useState, useEffect, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getGeneration } from "@/lib/api/ai";
import { getBeans } from "@/lib/api/beans";
import { createBlend } from "@/lib/api/blends";
import { BlendRecipeEditor, type RecipeRow } from "@/components/features/BlendRecipeEditor";
import { BLEND_STATUS, ROAST_LEVELS } from "@/product.config";
import type { CoffeeBean } from "@/lib/api/beans";
import { ApiError } from "@/lib/api/client";
import Link from "next/link";

export default function SaveBlendPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const generationId = searchParams.get("generation_id");

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [availableBeans, setAvailableBeans] = useState<CoffeeBean[]>([]);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [style, setStyle] = useState<"espresso" | "filter" | "milk">("espresso");
  const [rows, setRows] = useState<RecipeRow[]>([]);

  const [isPending, startTransition] = useTransition();
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setLoadError(null);
      try {
        const [beansData, genData] = await Promise.all([
          getBeans({ status: "AVAILABLE", per_page: 100 }),
          generationId ? getGeneration(generationId) : Promise.resolve(null),
        ]);

        setAvailableBeans(beansData.items);

        if (genData?.validated_output) {
          const draft = genData.validated_output as {
            blend_name: string;
            description: string;
            recipe: { coffee_bean_id: string; name: string; origin: string; percentage: number }[];
          };
          setName(draft.blend_name ?? "");
          setDescription(draft.description ?? "");
          setRows(draft.recipe.map((r) => ({
            coffee_bean_id: r.coffee_bean_id,
            name: r.name,
            origin: r.origin,
            percentage: r.percentage,
          })));
        }
      } catch (err) {
        setLoadError(err instanceof Error ? err.message : "Failed to load data.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [generationId]);

  const total = rows.reduce((s, r) => s + r.percentage, 0);
  const canSave = name.trim().length > 0 && rows.length >= 2 && rows.length <= 5 && total === 100 && !isPending;

  function handleSave() {
    if (!canSave) return;
    setSaveError(null);

    startTransition(async () => {
      try {
        const blend = await createBlend({
          name: name.trim(),
          description: description.trim() || undefined,
          style,
          items: rows.map((r) => ({ coffee_bean_id: r.coffee_bean_id, percentage: r.percentage })),
          source_generation_id: generationId ?? undefined,
        });
        router.push(`/dashboard/owner/blends/${blend.id}`);
      } catch (err) {
        if (err instanceof ApiError) {
          const body = err.body as { error?: string | object[] };
          setSaveError(typeof body?.error === "string" ? body.error : "Save failed. Please check your recipe.");
        } else {
          setSaveError("Something went wrong. Please try again.");
        }
      }
    });
  }

  if (loading) {
    return (
      <div className="py-16 text-center text-sm text-text-3">Loading…</div>
    );
  }

  if (loadError) {
    return (
      <div className="rounded-xl border border-danger/30 bg-danger/5 p-6 text-sm text-danger">
        {loadError}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl flex flex-col gap-6">
      <div>
        <div className="flex items-center gap-2 text-xs text-text-3 mb-1">
          <Link href="/dashboard/owner/blends" className="hover:text-text">My Blends</Link>
          <span>/</span>
          <span>Save blend</span>
        </div>
        <h1 className="text-xl font-semibold text-text">Save blend</h1>
        <p className="mt-1 text-sm text-text-3">
          Review the recipe, adjust percentages if needed, then save.
        </p>
      </div>

      {/* Name & description */}
      <div className="rounded-xl border border-border bg-surface p-5 flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-text">Blend name *</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={200}
            placeholder="e.g. Graveyard Shift"
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-3 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-text">Description</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={2000}
            rows={2}
            placeholder="Optional: describe the blend character"
            className="resize-none rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-3 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </label>

        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-text">Brew style</span>
          <div className="flex gap-2">
            {(["espresso", "milk", "filter"] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setStyle(s)}
                className={`rounded-lg border px-3 py-1.5 text-sm capitalize transition-colors ${
                  style === s
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-border text-text-2 hover:bg-surface-2"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Recipe editor */}
      <div className="rounded-xl border border-border bg-surface p-5">
        <h2 className="mb-4 text-sm font-semibold text-text">Recipe</h2>
        <BlendRecipeEditor
          initial={rows}
          availableBeans={availableBeans}
          onChange={setRows}
        />
      </div>

      {/* Save error */}
      {saveError && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 p-3 text-sm text-danger">
          {saveError}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={!canSave}
          className="rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          {isPending ? "Saving…" : "Save blend"}
        </button>
        <Link
          href="/dashboard/owner/blends"
          className="rounded-lg border border-border px-5 py-2.5 text-sm text-text-2 hover:text-text"
        >
          Cancel
        </Link>
      </div>
    </div>
  );
}
