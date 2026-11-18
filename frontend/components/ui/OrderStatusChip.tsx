import { ORDER_STATUS, type OrderStatus } from "@/product.config";

const TONE: Record<OrderStatus, string> = {
  PENDING: "bg-warning/10 text-warning",
  CONFIRMED: "bg-info/10 text-info",
  PREPARING: "bg-info/10 text-info",
  READY: "bg-info/10 text-info",
  SHIPPED: "bg-info/10 text-info",
  DELIVERED: "bg-success/10 text-success",
  COMPLETED: "bg-success/10 text-success",
  CANCELLED: "bg-surface-3 text-text-3",
};

export function OrderStatusChip({ status }: { status: OrderStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${TONE[status]}`}>
      {ORDER_STATUS[status].label}
    </span>
  );
}
