"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getOrders, type OrdersPage } from "@/lib/api/orders";
import { OrderCard } from "@/components/features/OrderCard";

type Tab = "active" | "past";

export default function OwnerOrdersPage() {
  const [tab, setTab] = useState<Tab>("active");
  const [page, setPage] = useState(1);
  const [loaded, setLoaded] = useState<{ key: string; data: OrdersPage } | null>(null);
  const [failedKey, setFailedKey] = useState<string | null>(null);

  const key = `${tab}:${page}`;

  useEffect(() => {
    let cancelled = false;
    getOrders({ active: tab === "active", page })
      .then((data) => {
        if (!cancelled) setLoaded({ key, data });
      })
      .catch(() => {
        if (!cancelled) setFailedKey(key);
      });
    return () => {
      cancelled = true;
    };
  }, [key, tab, page]);

  // A response only counts if it belongs to the tab and page on screen
  const current = loaded?.key === key ? loaded.data : null;
  const error = failedKey === key ? "Could not load your orders." : null;
  const loading = current === null && error === null;
  const orders = current?.items ?? [];
  const total = current?.total ?? 0;
  const pages = current?.pages ?? 1;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text">Orders</h1>
          <p className="mt-1 text-sm text-text-3">
            {total} {tab === "active" ? "open" : "finished"} order{total === 1 ? "" : "s"}
          </p>
        </div>
        <Link
          href="/dashboard/owner/beans"
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600"
        >
          + Order beans
        </Link>
      </div>

      <div className="flex gap-2">
        {(["active", "past"] as const).map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              setPage(1);
            }}
            className={`rounded-full px-3 py-1 text-sm capitalize transition-colors ${
              tab === t ? "bg-brand-500 text-white" : "border border-border text-text-2 hover:bg-surface-2"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {loading && <div className="py-16 text-center text-sm text-text-3">Loading…</div>}
      {error && (
        <div className="rounded-xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger">{error}</div>
      )}

      {current && orders.length === 0 && (
        <div className="rounded-xl border border-border bg-surface p-12 text-center">
          <p className="text-text-3">
            {tab === "active" ? "No open orders." : "No finished orders yet."}
          </p>
          {tab === "active" && (
            <p className="mt-2 text-sm text-text-3">
              Order a bean from the{" "}
              <Link href="/dashboard/owner/beans" className="text-brand-600 hover:underline">
                catalog
              </Link>{" "}
              or reorder one of your{" "}
              <Link href="/dashboard/owner/blends" className="text-brand-600 hover:underline">
                blends
              </Link>
              .
            </p>
          )}
        </div>
      )}

      {orders.length > 0 && (
        <div className="flex flex-col gap-4">
          {orders.map((order) => (
            <OrderCard
              key={order.id}
              order={order}
              perspective="owner"
              href={`/dashboard/owner/orders/${order.id}`}
            />
          ))}
        </div>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-text-3">
            {page} / {pages}
          </span>
          <button
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
