import Link from "next/link";
import type { ReorderItem } from "@/lib/api/insights";
import { REORDER_SOON_LABEL } from "@/product.config";

interface ReorderCardProps {
  items: ReorderItem[];
  /** Show blends that are fine too, not only the ones running low */
  showAll?: boolean;
}

function formatDays(days: number): string {
  if (days <= 0) return "No stock on hand";
  if (days < 1) return "Less than a day left";
  return `${Math.floor(days)} day${Math.floor(days) === 1 ? "" : "s"} left`;
}

export function ReorderCard({ items, showAll = false }: ReorderCardProps) {
  const visible = showAll ? items : items.filter((i) => i.reorder_soon);

  if (visible.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-surface p-5">
        <h2 className="text-sm font-semibold text-text">Reorder</h2>
        <p className="mt-2 text-sm text-text-3">
          {items.length === 0
            ? "Activate a blend with a daily usage and record the stock you hold. Reorder reminders appear here."
            : "Nothing is running low."}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <h2 className="text-sm font-semibold text-text">Reorder</h2>
      <ul className="mt-3 flex flex-col divide-y divide-border">
        {visible.map((item) => (
          <li key={item.blend_id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
            <div className="min-w-0">
              <p className="truncate font-medium text-text">{item.blend_name}</p>
              <p className="mt-0.5 text-xs text-text-3">
                {formatDays(item.days_remaining)} · {item.limiting_bean.name} runs out first
              </p>
            </div>
            <div className="flex items-center gap-3">
              {item.reorder_soon && (
                <span className="rounded-full bg-warning/10 px-2.5 py-0.5 text-xs font-medium text-warning">
                  {REORDER_SOON_LABEL}
                </span>
              )}
              <Link
                href={`/dashboard/owner/blends/${item.blend_id}#reorder`}
                className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-2 hover:bg-surface-2"
              >
                Order now
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
