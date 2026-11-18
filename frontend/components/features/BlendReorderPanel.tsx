"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import type { Blend } from "@/lib/api/blends";
import { errorMessage, reorderBlend } from "@/lib/api/orders";
import { formatPrice, UNITS } from "@/product.config";

/** Order every bean in a blend for a chosen total quantity. */
export function BlendReorderPanel({ blend }: { blend: Blend }) {
  const router = useRouter();
  const [totalKg, setTotalKg] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const total = parseFloat(totalKg);
  const valid = Number.isFinite(total) && total >= 1;

  // Preview only: the server recomputes quantities and prices from live data
  const lines = valid
    ? blend.items.map((item) => ({
        name: item.bean?.name ?? "Bean",
        kg: Math.round(total * item.percentage) / 100,
        price: item.bean?.price_per_kg ?? 0,
      }))
    : [];
  const estimate = lines.reduce((sum, l) => sum + l.kg * l.price, 0);
  const anyUnavailable = blend.items.some(
    (i) => i.bean && !["AVAILABLE", "LOW_STOCK"].includes(i.bean.status)
  );

  function submit() {
    if (!valid) return;
    setError(null);
    startTransition(async () => {
      try {
        await reorderBlend(blend.id, total);
        router.push("/dashboard/owner/orders");
      } catch (err) {
        setError(errorMessage(err, "Could not place the order."));
      }
    });
  }

  return (
    <div id="reorder" className="rounded-xl border border-border bg-surface p-6">
      <h2 className="text-sm font-semibold text-text">Reorder this blend</h2>
      <p className="mt-1 text-sm text-text-3">
        Enter how much finished blend you need. Each bean is ordered from its supplier in proportion
        to the recipe, one order per supplier.
      </p>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-xs text-text-3">Total quantity ({UNITS.weight})</span>
          <input
            type="number"
            min={1}
            step={0.5}
            value={totalKg}
            onChange={(e) => setTotalKg(e.target.value)}
            placeholder="e.g. 25"
            className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </label>
        <button
          onClick={submit}
          disabled={!valid || isPending || anyUnavailable}
          className="rounded-lg bg-brand-500 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isPending ? "Placing order…" : "Place order"}
        </button>
      </div>

      {anyUnavailable && (
        <p className="mt-3 text-sm text-warning">
          A bean in this recipe is unavailable. Find a substitute above before ordering.
        </p>
      )}

      {lines.length > 0 && (
        <ul className="mt-4 flex flex-col gap-1 text-sm text-text-2">
          {lines.map((l) => (
            <li key={l.name} className="flex justify-between">
              <span>{l.name}</span>
              <span className="tabular-nums">{l.kg} {UNITS.weight}</span>
            </li>
          ))}
          <li className="mt-1 flex justify-between border-t border-border pt-2 font-medium text-text">
            <span>Estimated total</span>
            <span className="tabular-nums">{formatPrice(estimate)}</span>
          </li>
        </ul>
      )}

      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
    </div>
  );
}
