import {
  ORDER_PENDING_NOTE,
  ORDER_STATUS,
  ORDER_TIMELINE,
  ORDER_TIMELINE_LABELS,
  type OrderStatus,
} from "@/product.config";

/**
 * Five segments (labels from product.config). PENDING shows them all dim with
 * an "Awaiting supplier" note, COMPLETED shows them all filled, CANCELLED shows
 * them dim with a cancelled note.
 */
export function OrderTimeline({ status }: { status: OrderStatus }) {
  const step = ORDER_STATUS[status].step;
  const cancelled = status === "CANCELLED";

  return (
    <div>
      <ol className="grid grid-cols-5 gap-1.5" aria-label={`Order progress: ${ORDER_STATUS[status].label}`}>
        {ORDER_TIMELINE.map((segment, i) => {
          const filled = !cancelled && step >= i + 1;
          const current = !cancelled && step === i + 1;
          return (
            <li key={segment} className="flex flex-col gap-1.5">
              <span
                className={`h-1.5 rounded-full ${filled ? "bg-brand-500" : "bg-surface-3"} ${
                  current ? "ring-2 ring-brand-200" : ""
                }`}
              />
              <span
                className={`text-[11px] leading-tight ${
                  filled ? "font-medium text-text" : "text-text-3"
                }`}
              >
                {ORDER_TIMELINE_LABELS[segment]}
              </span>
            </li>
          );
        })}
      </ol>
      {status === "PENDING" && <p className="mt-2 text-xs text-text-3">{ORDER_PENDING_NOTE}</p>}
      {cancelled && <p className="mt-2 text-xs text-danger">This order was cancelled.</p>}
    </div>
  );
}
