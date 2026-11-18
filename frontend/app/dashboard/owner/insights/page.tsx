"use client";

import { useEffect, useState, useTransition } from "react";
import {
  getOwnerStock,
  getReorder,
  getSpend,
  getVolume,
  setOwnerStock,
  type ReorderItem,
  type SpendResponse,
  type StockRow,
  type VolumeResponse,
} from "@/lib/api/insights";
import { errorMessage } from "@/lib/api/orders";
import { ReorderCard } from "@/components/features/ReorderCard";
import { SpendChart } from "@/components/features/SpendChart";
import { formatPrice, UNITS } from "@/product.config";

const MONTHS = 6;

interface Loaded {
  spend: SpendResponse;
  volume: VolumeResponse;
  reorder: ReorderItem[];
  stock: StockRow[];
}

export default function InsightsPage() {
  const [data, setData] = useState<Loaded | null>(null);
  const [failed, setFailed] = useState(false);
  const [reload, setReload] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [stockError, setStockError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    let cancelled = false;
    Promise.all([getSpend(MONTHS), getVolume(MONTHS), getReorder(), getOwnerStock()])
      .then(([spend, volume, reorder, stock]) => {
        if (cancelled) return;
        setData({ spend, volume, reorder: reorder.items, stock: stock.items });
        setFailed(false);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [reload]);

  function saveStock(row: StockRow) {
    const value = parseFloat(drafts[row.coffee_bean_id] ?? "");
    if (!Number.isFinite(value) || value < 0) {
      setStockError("Enter a quantity of 0 or more.");
      return;
    }
    setStockError(null);
    startTransition(async () => {
      try {
        await setOwnerStock(row.coffee_bean_id, value);
        setDrafts((d) => {
          const rest = { ...d };
          delete rest[row.coffee_bean_id];
          return rest;
        });
        setReload((n) => n + 1); // reorder days depend on stock, so refetch everything
      } catch (err) {
        setStockError(errorMessage(err, "Could not update stock."));
      }
    });
  }

  if (failed && !data) {
    return (
      <div className="rounded-xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger">
        Could not load your insights.
      </div>
    );
  }
  if (!data) return <div className="py-16 text-center text-sm text-text-3">Loading…</div>;

  const { spend, volume, reorder, stock } = data;
  const totalSpend = spend.items.reduce((s, m) => s + m.amount, 0);
  const totalKg = volume.items.reduce((s, m) => s + m.kg, 0);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text">Insights</h1>
        <p className="mt-1 text-sm text-text-3">
          Spending, volume and reorder reminders from your orders. Cancelled orders are not counted.
        </p>
      </div>

      <ReorderCard items={reorder} showAll />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="text-sm font-semibold text-text">Monthly spend</h2>
            <span className="text-xs text-text-3">Last {MONTHS} months: {formatPrice(totalSpend)}</span>
          </div>
          <SpendChart
            label="Spend"
            data={spend.items.map((m) => ({ month: m.month, value: m.amount }))}
            format={(v) => formatPrice(v)}
          />
        </div>

        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="text-sm font-semibold text-text">Monthly volume</h2>
            <span className="text-xs text-text-3">Last {MONTHS} months: {totalKg.toFixed(1)} {UNITS.weight}</span>
          </div>
          <SpendChart
            label="Volume"
            data={volume.items.map((m) => ({ month: m.month, value: m.kg }))}
            format={(v) => `${v} ${UNITS.weight}`}
          />
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface p-5">
        <h2 className="text-sm font-semibold text-text">Stock on hand</h2>
        <p className="mt-1 text-sm text-text-3">
          Delivered orders add to this automatically. Correct it here after you use or count beans;
          reorder reminders are calculated from these figures.
        </p>
        {stockError && <p role="alert" className="mt-3 text-sm text-danger">{stockError}</p>}

        {stock.length === 0 ? (
          <p className="mt-4 text-sm text-text-3">
            Nothing recorded yet. Stock appears once an order is delivered.
          </p>
        ) : (
          <ul className="mt-4 flex flex-col divide-y divide-border">
            {stock.map((row) => {
              const draft = drafts[row.coffee_bean_id];
              const dirty = draft !== undefined && draft !== String(row.quantity_kg);
              return (
                <li key={row.coffee_bean_id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                  <div>
                    <p className="text-sm font-medium text-text">{row.name}</p>
                    <p className="text-xs text-text-3">{row.origin}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={0}
                      step={0.5}
                      aria-label={`${row.name} stock in ${UNITS.weight}`}
                      value={draft ?? String(row.quantity_kg)}
                      onChange={(e) => setDrafts((d) => ({ ...d, [row.coffee_bean_id]: e.target.value }))}
                      className="w-24 rounded-lg border border-border bg-surface px-2 py-1.5 text-right text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                    <span className="text-sm text-text-3">{UNITS.weight}</span>
                    <button
                      onClick={() => saveStock(row)}
                      disabled={!dirty || isPending}
                      className="rounded-lg border border-border px-3 py-1.5 text-xs text-text-2 hover:bg-surface-2 disabled:opacity-40"
                    >
                      Save
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
