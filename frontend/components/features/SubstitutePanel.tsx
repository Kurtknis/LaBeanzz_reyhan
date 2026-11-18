"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import type { Blend } from "@/lib/api/blends";
import { substituteBean, type GenerateBlendResponse } from "@/lib/api/ai";
import { errorMessage } from "@/lib/api/orders";
import { RecipePercentageBar } from "./RecipePercentageBar";

const AVAILABLE = ["AVAILABLE", "LOW_STOCK"];

/** Shows a warning when a bean in the blend has run out, and proposes a re-balanced recipe. */
export function SubstitutePanel({ blend }: { blend: Blend }) {
  const [result, setResult] = useState<GenerateBlendResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const missing = blend.items.filter((i) => i.bean && !AVAILABLE.includes(i.bean.status));
  if (missing.length === 0) return null;

  function run() {
    setError(null);
    setResult(null);
    startTransition(async () => {
      try {
        setResult(await substituteBean({ blend_id: blend.id }));
      } catch (err) {
        setError(errorMessage(err, "Could not find a substitute. Please try again."));
      }
    });
  }

  return (
    <div className="rounded-xl border border-warning/40 bg-warning/5 p-6">
      <h2 className="text-sm font-semibold text-warning">
        {missing.length === 1 ? "A bean in this blend is unavailable" : "Some beans in this blend are unavailable"}
      </h2>
      <p className="mt-1 text-sm text-text-2">
        {missing.map((m) => m.bean?.name).join(", ")} can&apos;t be ordered right now. Ask for a
        re-balanced recipe that keeps the flavor close to the original. Nothing changes until you
        save the result.
      </p>

      <button
        onClick={run}
        disabled={isPending}
        className="mt-4 rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
      >
        {isPending ? "Looking for a substitute…" : result ? "Try again" : "Find a substitute"}
      </button>

      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}

      {result && (
        <div className="mt-5 flex flex-col gap-4 rounded-lg border border-border bg-surface p-4">
          <div>
            <p className="font-semibold text-text">{result.draft.blend_name}</p>
            <p className="mt-0.5 text-sm text-text-2">{result.draft.description}</p>
          </div>
          <RecipePercentageBar recipe={result.draft.recipe} />
          <p className="text-sm leading-relaxed text-text-2">{result.draft.reasoning}</p>
          <Link
            href={`/dashboard/owner/blends/save?generation_id=${result.generation_id}`}
            className="self-start rounded-lg border border-brand-500 px-4 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-50"
          >
            Review and save as a new blend →
          </Link>
        </div>
      )}
    </div>
  );
}
