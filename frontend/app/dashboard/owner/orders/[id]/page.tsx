"use client";

import { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ApiError } from "@/lib/api/client";
import { errorMessage, getOrder, updateOrderStatus, type Order } from "@/lib/api/orders";
import { OrderStatusChip } from "@/components/ui/OrderStatusChip";
import { OrderTimeline } from "@/components/features/OrderTimeline";
import { formatPrice, OWNER_CANCELLABLE, UNITS } from "@/product.config";

type Loaded = { id: string; order: Order | null; failure: "notfound" | "error" | null };

export default function OwnerOrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [reload, setReload] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    let cancelled = false;
    getOrder(id)
      .then((order) => {
        if (!cancelled) setLoaded({ id, order, failure: null });
      })
      .catch((err) => {
        if (cancelled) return;
        const failure = err instanceof ApiError && err.status === 404 ? "notfound" : "error";
        setLoaded({ id, order: null, failure });
      });
    return () => {
      cancelled = true;
    };
  }, [id, reload]);

  function act(status: "CANCELLED" | "COMPLETED") {
    setActionError(null);
    startTransition(async () => {
      try {
        const order = await updateOrderStatus(id, status);
        setLoaded({ id, order, failure: null });
      } catch (err) {
        setActionError(errorMessage(err, "Could not update the order."));
        setReload((n) => n + 1); // show what the order looks like now
      }
    });
  }

  const current = loaded?.id === id ? loaded : null;
  if (current === null) return <div className="py-16 text-center text-sm text-text-3">Loading…</div>;

  if (current.failure === "notfound") {
    return (
      <div className="rounded-xl border border-border bg-surface p-12 text-center">
        <p className="text-text-3">This order does not exist.</p>
        <Link href="/dashboard/owner/orders" className="mt-3 inline-block text-sm text-brand-600 hover:underline">
          Back to orders
        </Link>
      </div>
    );
  }
  const order = current.order;
  if (!order) {
    return (
      <div className="rounded-xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger">
        Could not load this order.
      </div>
    );
  }

  const canCancel = OWNER_CANCELLABLE.includes(order.status);
  const canComplete = order.status === "DELIVERED";

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="flex items-center gap-2 text-xs text-text-3">
        <Link href="/dashboard/owner/orders" className="hover:text-text">Orders</Link>
        <span>/</span>
        <span>{order.supplier.business_name ?? "Order"}</span>
      </div>

      <div className="rounded-xl border border-border bg-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-text">{order.supplier.business_name ?? "Order"}</h1>
            <p className="mt-1 text-sm text-text-3">
              Placed {new Date(order.created_at).toLocaleString()}
              {order.eta_date ? ` · ETA ${new Date(order.eta_date).toLocaleDateString()}` : ""}
            </p>
          </div>
          <OrderStatusChip status={order.status} />
        </div>
        <div className="mt-6">
          <OrderTimeline status={order.status} />
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface p-6">
        <h2 className="mb-4 text-sm font-semibold text-text">Items</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-3">
              <th className="pb-2 font-medium">Bean</th>
              <th className="pb-2 text-right font-medium">Quantity</th>
              <th className="pb-2 text-right font-medium">Price/{UNITS.weight}</th>
              <th className="pb-2 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {order.items.map((item) => (
              <tr key={item.id} className="border-b border-border/50 last:border-0">
                <td className="py-2 pr-3">
                  <Link href={`/dashboard/owner/beans/${item.coffee_bean_id}`} className="font-medium text-text hover:text-brand-600">
                    {item.name ?? "Bean"}
                  </Link>
                  {item.origin && <span className="ml-2 text-xs text-text-3">{item.origin}</span>}
                </td>
                <td className="py-2 text-right tabular-nums">{item.quantity_kg} {UNITS.weight}</td>
                <td className="py-2 text-right tabular-nums text-text-3">{formatPrice(item.unit_price)}</td>
                <td className="py-2 text-right tabular-nums">{formatPrice(item.line_total)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3} className="pt-3 text-right text-xs text-text-3">Order total</td>
              <td className="pt-3 text-right font-semibold tabular-nums text-text">{formatPrice(order.total_price)}</td>
            </tr>
          </tfoot>
        </table>
        <p className="mt-3 text-xs text-text-3">Prices are those listed when you placed the order.</p>
        {order.source_blend_id && (
          <p className="mt-2 text-sm">
            <Link href={`/dashboard/owner/blends/${order.source_blend_id}`} className="text-brand-600 hover:underline">
              Ordered from a blend →
            </Link>
          </p>
        )}
      </div>

      {(canCancel || canComplete || actionError) && (
        <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface-2 p-5">
          {actionError && <p role="alert" className="text-sm text-danger">{actionError}</p>}
          <div className="flex flex-wrap gap-2">
            {canComplete && (
              <button
                onClick={() => act("COMPLETED")}
                disabled={isPending}
                className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                Mark as received
              </button>
            )}
            {canCancel && (
              <button
                onClick={() => {
                  if (confirm("Cancel this order? The reserved beans go back to the supplier.")) act("CANCELLED");
                }}
                disabled={isPending}
                className="rounded-lg border border-danger/40 px-4 py-2 text-sm text-danger hover:bg-danger/5 disabled:opacity-50"
              >
                Cancel order
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
