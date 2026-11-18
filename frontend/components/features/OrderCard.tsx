import Link from "next/link";
import type { ReactNode } from "react";
import type { Order } from "@/lib/api/orders";
import { OrderStatusChip } from "@/components/ui/OrderStatusChip";
import { OrderTimeline } from "./OrderTimeline";
import { formatPrice, UNITS } from "@/product.config";

interface OrderCardProps {
  order: Order;
  perspective: "owner" | "supplier";
  /** Link target for the card title (owners get a detail page) */
  href?: string;
  actions?: ReactNode;
}

export function OrderCard({ order, perspective, href, actions }: OrderCardProps) {
  const counterparty =
    perspective === "owner" ? order.supplier.business_name : order.owner?.business_name;
  const placed = new Date(order.created_at).toLocaleDateString();
  const title = counterparty ?? "Order";

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          {href ? (
            <Link href={href} className="font-semibold text-text hover:text-brand-600">
              {title}
            </Link>
          ) : (
            <p className="font-semibold text-text">{title}</p>
          )}
          <p className="mt-0.5 text-xs text-text-3">
            {perspective === "owner" ? "Placed" : "Ordered by this café on"} {placed}
            {order.eta_date ? ` · ETA ${new Date(order.eta_date).toLocaleDateString()}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold tabular-nums text-text">
            {formatPrice(order.total_price)}
          </span>
          <OrderStatusChip status={order.status} />
        </div>
      </div>

      <ul className="flex flex-wrap gap-1.5">
        {order.items.map((item) => (
          <li key={item.id} className="rounded-full bg-surface-2 px-2.5 py-0.5 text-xs text-text-2">
            {item.name ?? "Bean"} · {item.quantity_kg} {UNITS.weight}
          </li>
        ))}
      </ul>

      <OrderTimeline status={order.status} />

      {actions && <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">{actions}</div>}
    </div>
  );
}
