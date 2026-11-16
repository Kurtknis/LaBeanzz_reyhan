"use client";

import { useState } from "react";
import type { CoffeeBean } from "@/lib/api/beans";

export interface RecipeRow {
  coffee_bean_id: string;
  name: string;
  origin: string;
  percentage: number;
}

interface BlendRecipeEditorProps {
  initial: RecipeRow[];
  availableBeans: CoffeeBean[];
  onChange: (rows: RecipeRow[]) => void;
}

export function BlendRecipeEditor({ initial, availableBeans, onChange }: BlendRecipeEditorProps) {
  const [rows, setRows] = useState<RecipeRow[]>(initial);

  const total = rows.reduce((s, r) => s + r.percentage, 0);
  const isValid = total === 100 && rows.length >= 2 && rows.length <= 5;

  function update(updated: RecipeRow[]) {
    setRows(updated);
    onChange(updated);
  }

  function handlePctChange(idx: number, raw: string) {
    const val = Math.min(100, Math.max(1, parseInt(raw) || 0));
    const next = rows.map((r, i) => (i === idx ? { ...r, percentage: val } : r));
    update(next);
  }

  function handleRemove(idx: number) {
    update(rows.filter((_, i) => i !== idx));
  }

  function handleAdd(beanId: string) {
    if (!beanId || rows.length >= 5) return;
    const already = rows.find((r) => r.coffee_bean_id === beanId);
    if (already) return;
    const bean = availableBeans.find((b) => b.id === beanId);
    if (!bean) return;

    // Start new bean at 10%, redistribute evenly so total stays near 100
    const newRow: RecipeRow = { coffee_bean_id: bean.id, name: bean.name, origin: bean.origin, percentage: 10 };
    const next = [...rows, newRow];
    // Balance: subtract proportionally from existing rows
    const excess = next.reduce((s, r) => s + r.percentage, 0) - 100;
    if (excess > 0 && rows.length > 0) {
      const perRow = Math.floor(excess / rows.length);
      let rem = excess - perRow * rows.length;
      for (let i = 0; i < next.length - 1; i++) {
        const cut = perRow + (rem > 0 ? 1 : 0);
        rem = Math.max(0, rem - 1);
        next[i] = { ...next[i], percentage: Math.max(1, next[i].percentage - cut) };
      }
    }
    update(next);
  }

  const usedIds = new Set(rows.map((r) => r.coffee_bean_id));
  const unusedBeans = availableBeans.filter((b) => !usedIds.has(b.id));

  return (
    <div className="flex flex-col gap-4">
      {/* Rows */}
      <div className="flex flex-col gap-2">
        {rows.map((row, idx) => (
          <div
            key={row.coffee_bean_id}
            className="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3"
          >
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm text-text truncate">{row.name}</p>
              <p className="text-xs text-text-3">{row.origin}</p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <input
                type="number"
                min={1}
                max={100}
                value={row.percentage}
                onChange={(e) => handlePctChange(idx, e.target.value)}
                className="w-16 rounded border border-border bg-surface-2 px-2 py-1 text-center text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-brand-500"
                aria-label={`${row.name} percentage`}
              />
              <span className="text-sm text-text-3">%</span>

              {rows.length > 2 && (
                <button
                  type="button"
                  onClick={() => handleRemove(idx)}
                  className="rounded p-1 text-text-3 hover:text-danger"
                  aria-label={`Remove ${row.name}`}
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Total indicator */}
      <div className={`flex items-center justify-between rounded-lg px-4 py-2.5 text-sm ${
        total === 100
          ? "bg-success/10 text-success"
          : total > 100
          ? "bg-danger/10 text-danger"
          : "bg-warning/10 text-warning"
      }`}>
        <span>Total</span>
        <span className="font-semibold tabular-nums">
          {total}%{total !== 100 && (total > 100 ? " — over by " + (total - 100) + "%" : " — " + (100 - total) + "% remaining")}
        </span>
      </div>

      {/* Add bean */}
      {rows.length < 5 && unusedBeans.length > 0 && (
        <div className="flex gap-2">
          <select
            defaultValue=""
            onChange={(e) => { handleAdd(e.target.value); e.target.value = ""; }}
            className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Add a bean to the recipe"
          >
            <option value="" disabled>+ Add a bean…</option>
            {unusedBeans.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name} ({b.origin})
              </option>
            ))}
          </select>
        </div>
      )}

      {!isValid && (
        <p className="text-xs text-text-3">
          {rows.length < 2
            ? "A blend needs at least 2 beans."
            : rows.length > 5
            ? "A blend can have at most 5 beans."
            : total !== 100
            ? "Percentages must add up to exactly 100% before you can save."
            : ""}
        </p>
      )}
    </div>
  );
}
