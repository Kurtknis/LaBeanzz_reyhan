"use client";

import { useEffect, useState, useTransition } from "react";
import { errorMessage, getOrders, updateOrderStatus, type Order } from "@/lib/api/orders";
import { OrderCard } from "@/components/features/OrderCard";
import {
  SUPPLIER_ACTION_LABEL,
  SUPPLIER_NEXT_STATUS,
  type OrderStatus,
} from "@/product.config";

type Tab = "active" | "past";

export default function SupplierOrdersPage() {
  const [tab, setTab] = useState<Tab>("active");
  const [reload, setReload] = useState(0);
  const [loaded, setLoaded] = useState<{ key: string; orders: Order[] } | null>(null);
  const [failedKey, setFailedKey] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [eta, setEta] = useState<Record<string, string>>({});
  const [isPending, startTransition] = useTransition();

  const key = `${tab}:${reload}`;

  useEffect(() => {
    let cancelled = false;
    getOrders({ active: tab === "active", per_page: 100 })
      .then((data) => {
        if (!cancelled) setLoaded({ key, orders: data.items });
      })
      .catch(() => {
        if (!cancelled) setFailedKey(key);
      });
    return () => {
      cancelled = true;
    };
  }, [key, tab]);

  const current = loaded?.key === key ? loaded : null;
  const error = failedKey === key ? "Could not load orders." : null;
  const loading = current === null && error === null;
  const orders = current?.orders ?? [];

  function advance(order: Order, next: OrderStatus) {
    setActionError(null);
    startTransition(async () => {
      try {
        const updated = await updateOrderStatus(order.id, next, eta[order.id] || undefined);
        setLoaded((prev) =>
          prev ? { ...prev, orders: prev.orders.map((o) => (o.id === order.id ? updated : o)) } : prev
        );
      } catch (err) {
        setActionError(errorMessage(err, "Could not update the order."));
        setReload((n) => n + 1); // pick up whatever state the order is really in
      }
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text">Orders</h1>
        <p className="mt-1 text-sm text-text-3">Orders placed with you. Move each one forward as you fulfil it.</p>
      </div>

      <div className="flex gap-2">
        {(["active", "past"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-full px-3 py-1 text-sm capitalize transition-colors ${
              tab === t ? "bg-brand-500 text-white" : "border border-border text-text-2 hover:bg-surface-2"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {actionError && (
        <div role="alert" className="rounded-lg border border-danger/30 bg-danger/5 p-3 text-sm text-danger">
          {actionError}
        </div>
      )}
      {loading && <div className="py-16 text-center text-sm text-text-3">Loading…</div>}
      {error && (
        <div className="rounded-xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger">{error}</div>
      )}

      {current && orders.length === 0 && (
        <div className="rounded-xl border border-border bg-surface p-12 text-center">
          <p className="text-text-3">{tab === "active" ? "No open orders right now." : "No finished orders yet."}</p>
        </div>
      )}

      {orders.length > 0 && (
        <div className="flex flex-col gap-4">
          {orders.map((order) => {
            const next = SUPPLIER_NEXT_STATUS[order.status];
            return (
              <OrderCard
                key={order.id}
                order={order}
                perspective="supplier"
                actions={
                  next ? (
                    <>
                      {next === "SHIPPED" && (
                        <label className="flex items-center gap-2 text-xs text-text-3">
                          ETA
                          <input
                            type="date"
                            value={eta[order.id] ?? ""}
                            onChange={(e) => setEta((prev) => ({ ...prev, [order.id]: e.target.value }))}
                            className="rounded-lg border border-border bg-surface px-2 py-1 text-sm text-text"
                          />
                        </label>
                      )}
                      <button
                        onClick={() => advance(order, next)}
                        disabled={isPending}
                        className="rounded-lg bg-brand-500 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-50"
                      >
                        {SUPPLIER_ACTION_LABEL[next] ?? "Advance"}
                      </button>
                    </>
                  ) : undefined
                }
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
