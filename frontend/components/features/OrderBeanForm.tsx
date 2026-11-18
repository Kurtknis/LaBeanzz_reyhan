"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { createOrder, errorMessage } from "@/lib/api/orders";
import { formatPrice, UNITS } from "@/product.config";

interface OrderBeanFormProps {
  beanId: string;
  pricePerKg: number;
  stockKg: number;
}

export function OrderBeanForm({ beanId, pricePerKg, stockKg }: OrderBeanFormProps) {
  const router = useRouter();
  const [quantity, setQuantity] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const kg = parseFloat(quantity);
  const valid = Number.isFinite(kg) && kg > 0 && kg <= stockKg;

  function submit() {
    if (!valid) return;
    setError(null);
    startTransition(async () => {
      try {
        await createOrder({ items: [{ coffee_bean_id: beanId, quantity_kg: kg }] });
        router.push("/dashboard/owner/orders");
      } catch (err) {
        setError(errorMessage(err, "Could not place the order."));
      }
    });
  }

  return (
    <div className="rounded-xl border border-border bg-surface p-6">
      <h2 className="text-sm font-semibold text-text">Order this bean</h2>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-xs text-text-3">
            Quantity ({UNITS.weight}, up to {stockKg})
          </span>
          <input
            type="number"
            min={0.1}
            max={stockKg}
            step={0.5}
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-32 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </label>
        <button
          onClick={submit}
          disabled={!valid || isPending}
          className="rounded-lg bg-brand-500 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isPending ? "Placing order…" : "Place order"}
        </button>
        {valid && (
          <span className="pb-2 text-sm text-text-2 tabular-nums">{formatPrice(kg * pricePerKg)}</span>
        )}
      </div>
      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
    </div>
  );
}
