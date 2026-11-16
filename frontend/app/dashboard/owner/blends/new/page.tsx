"use client";

import { useState, useTransition, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  generateBlend,
  type BlendDraft,
  type BlendStyle,
} from "@/lib/api/ai";
import { getPresets, type Preset } from "@/lib/api/presets";
import { ApiError } from "@/lib/api/client";
import { RecipePercentageBar } from "@/components/features/RecipePercentageBar";
import { AIReasoningPanel } from "@/components/features/AIReasoningPanel";
import { GenerationLoader } from "@/components/features/GenerationLoader";
import { FLAVOR_AXES } from "@/product.config";

const STYLES: { value: BlendStyle; label: string; hint: string }[] = [
  { value: "espresso", label: "Espresso",    hint: "Bold, concentrated, works as a black shot" },
  { value: "milk",     label: "Milk drinks", hint: "Latte, flat white, cappuccino — lower acidity needed" },
  { value: "filter",   label: "Filter",      hint: "Pour-over, drip — bright and tea-like" },
];

const EXAMPLE_PROMPTS = [
  "Bold espresso with dark chocolate and caramel, low acidity, heavy body",
  "Bright, fruity filter coffee with berry and citrus notes",
  "Smooth latte base, chocolatey and sweet, easy on the stomach",
  "Complex specialty espresso, floral and stone fruit, medium body",
];

export default function NewBlendPage() {
  const searchParams = useSearchParams();
  const urlPresetId = searchParams.get("preset_id");

  const [prompt, setPrompt]           = useState("");
  const [style, setStyle]             = useState<BlendStyle>("espresso");
  const [maxPrice, setMaxPrice]       = useState("");
  const [isPending, startTransition]  = useTransition();
  const [draft, setDraft]             = useState<BlendDraft | null>(null);
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [error, setError]             = useState<string | null>(null);

  const [presets, setPresets]         = useState<Preset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>(urlPresetId ?? "");

  useEffect(() => {
    getPresets().then((r) => setPresets(r.items)).catch(() => {});
  }, []);

  // When a preset is selected, pre-fill style
  useEffect(() => {
    if (!selectedPresetId) return;
    const p = presets.find((pr) => pr.id === selectedPresetId);
    if (p?.coffee_style) setStyle(p.coffee_style as BlendStyle);
  }, [selectedPresetId, presets]);

  function handleExampleClick(text: string) {
    setPrompt(text);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim() || isPending) return;

    setError(null);
    setDraft(null);
    setGenerationId(null);

    startTransition(async () => {
      try {
        const result = await generateBlend({
          prompt: prompt.trim(),
          style,
          preset_id: selectedPresetId || null,
          max_price_per_kg: maxPrice ? parseFloat(maxPrice) : null,
        });
        setDraft(result.draft);
        setGenerationId(result.generation_id);
      } catch (err) {
        if (err instanceof ApiError) {
          const body = err.body as { error?: string | object };
          const msg =
            typeof body?.error === "string"
              ? body.error
              : "The AI could not produce a valid blend. Try rephrasing your prompt.";
          setError(msg);
        } else {
          setError("Something went wrong. Please try again.");
        }
      }
    });
  }

  return (
    <div className="mx-auto max-w-3xl">
      {/* Page header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-xs text-text-3 mb-1">
          <Link href="/dashboard/owner/blends" className="hover:text-text">
            My Blends
          </Link>
          <span>/</span>
          <span>New blend</span>
        </div>
        <h1 className="text-xl font-semibold text-text">New Blend</h1>
        <p className="mt-1 text-sm text-text-3">
          Describe the coffee you want. The AI picks beans from the current
          catalog and builds a validated recipe.
        </p>
      </div>

      {/* Form */}
      <form
        onSubmit={handleSubmit}
        className="rounded-xl border border-border bg-surface p-6"
      >
        {/* Prompt */}
        <div className="flex flex-col gap-1.5 mb-5">
          <label
            htmlFor="prompt"
            className="text-sm font-medium text-text"
          >
            Describe your blend
          </label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            maxLength={1000}
            placeholder="e.g. Bold espresso with dark chocolate, low acidity, heavy body…"
            className="resize-none rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-3 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          {/* Example prompts */}
          <div className="flex flex-wrap gap-1.5 mt-1">
            {EXAMPLE_PROMPTS.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => handleExampleClick(ex)}
                className="rounded-full border border-border px-2.5 py-0.5 text-xs text-text-3 hover:border-brand-400 hover:text-brand-700 transition-colors"
              >
                {ex.length > 40 ? ex.slice(0, 40) + "…" : ex}
              </button>
            ))}
          </div>
        </div>

        {/* Style selector */}
        <div className="mb-5">
          <span className="block text-sm font-medium text-text mb-2">
            Brew style
          </span>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {STYLES.map((s) => (
              <label
                key={s.value}
                className={`flex cursor-pointer flex-col gap-0.5 rounded-lg border-2 px-3 py-2.5 transition-colors ${
                  style === s.value
                    ? "border-brand-500 bg-brand-50"
                    : "border-border hover:bg-surface-2"
                }`}
              >
                <input
                  type="radio"
                  name="style"
                  value={s.value}
                  checked={style === s.value}
                  onChange={() => setStyle(s.value)}
                  className="sr-only"
                />
                <span className="text-sm font-medium text-text">{s.label}</span>
                <span className="text-xs text-text-3">{s.hint}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Max price */}
        <div className="mb-6 flex flex-col gap-1.5">
          <label
            htmlFor="maxPrice"
            className="text-sm font-medium text-text"
          >
            Max price per kg{" "}
            <span className="font-normal text-text-3">(optional)</span>
          </label>
          <div className="relative w-40">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-text-3">
              $
            </span>
            <input
              id="maxPrice"
              type="number"
              min="0"
              step="0.01"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
              placeholder="Any"
              className="w-full rounded-lg border border-border bg-surface py-2 pl-7 pr-3 text-sm text-text placeholder:text-text-3 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        {/* Preset selector */}
        {presets.length > 0 && (
          <div className="mb-6 flex flex-col gap-1.5">
            <label htmlFor="preset" className="text-sm font-medium text-text">
              Preset{" "}
              <span className="font-normal text-text-3">(optional)</span>
            </label>
            <select
              id="preset"
              value={selectedPresetId}
              onChange={(e) => setSelectedPresetId(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">No preset</option>
              {presets.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
        )}

        {error && (
          <p
            role="alert"
            className="mb-4 rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger"
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={!prompt.trim() || isPending}
          className="rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          {isPending ? "Generating…" : "Generate blend"}
        </button>
      </form>

      {/* Loader */}
      <GenerationLoader active={isPending} />

      {/* Result */}
      {draft && !isPending && (
        <div className="mt-8 flex flex-col gap-6">
          {/* Blend header */}
          <div className="rounded-xl border border-border bg-surface p-6">
            <div className="mb-1 flex items-start justify-between gap-4">
              <h2 className="text-lg font-semibold text-text">
                {draft.blend_name}
              </h2>
              <span className="shrink-0 rounded-full bg-brand-100 px-2.5 py-0.5 text-xs font-medium text-brand-800">
                Draft
              </span>
            </div>
            <p className="text-sm text-text-2 leading-relaxed">
              {draft.description}
            </p>
          </div>

          {/* Recipe bar */}
          <div className="rounded-xl border border-border bg-surface p-6">
            <h3 className="mb-4 text-sm font-semibold text-text">Recipe</h3>
            <RecipePercentageBar recipe={draft.recipe} />

            {/* Bean details table */}
            <div className="mt-5 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-text-3">
                    <th className="pb-2 pr-4 font-medium">Bean</th>
                    <th className="pb-2 pr-4 font-medium">Origin</th>
                    <th className="pb-2 font-medium text-right">%</th>
                  </tr>
                </thead>
                <tbody>
                  {draft.recipe.map((item) => (
                    <tr
                      key={item.coffee_bean_id}
                      className="border-b border-border/50 last:border-0"
                    >
                      <td className="py-2 pr-4 font-medium text-text">
                        {item.name}
                      </td>
                      <td className="py-2 pr-4 text-text-3">{item.origin}</td>
                      <td className="py-2 text-right font-semibold text-text">
                        {item.percentage}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Profile + reasoning */}
          <div className="rounded-xl border border-border bg-surface p-6">
            <AIReasoningPanel draft={draft} />
          </div>

          {/* Save CTA */}
          <div className="flex items-center justify-between rounded-xl border border-border bg-surface-2 px-5 py-4">
            <p className="text-sm text-text-2">
              Happy with this recipe? Save it to My Blends.
            </p>
            <Link
              href={`/dashboard/owner/blends/save?generation_id=${generationId}`}
              className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-600"
            >
              Save blend →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
