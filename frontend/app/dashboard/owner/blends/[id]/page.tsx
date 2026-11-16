import { notFound } from "next/navigation";
import Link from "next/link";
import { getBlend } from "@/lib/api/blends";
import { ApiError } from "@/lib/api/client";
import { FlavorBar } from "@/components/ui/FlavorBar";
import { BLEND_STATUS, type BlendStatus } from "@/product.config";
import { BlendActions } from "./BlendActions";
import { FeedbackSection } from "@/components/features/FeedbackSection";

export const instant = false;

interface Props {
  params: Promise<{ id: string }>;
}

function StatusBadge({ status }: { status: BlendStatus }) {
  const config = BLEND_STATUS[status];
  const colors: Record<BlendStatus, string> = {
    DRAFT: "bg-info/10 text-info",
    ACTIVE: "bg-success/10 text-success",
    ARCHIVED: "bg-surface-3 text-text-3",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${colors[status]}`}>
      {config.label}
    </span>
  );
}

export default async function BlendDetailPage({ params }: Props) {
  const { id } = await params;

  let blend;
  try {
    blend = await getBlend(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  const computed = blend.predicted_profile?.computed;
  const totalPct = blend.items.reduce((s, i) => s + i.percentage, 0);

  return (
    <div className="mx-auto max-w-2xl flex flex-col gap-6">
      <div className="flex items-center gap-2 text-xs text-text-3">
        <Link href="/dashboard/owner/blends" className="hover:text-text">My Blends</Link>
        <span>/</span>
        <span className="truncate">{blend.name}</span>
      </div>

      {/* Header */}
      <div className="rounded-xl border border-border bg-surface p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-semibold text-text">{blend.name}</h1>
            {blend.description && (
              <p className="mt-1 text-sm leading-relaxed text-text-2">{blend.description}</p>
            )}
          </div>
          <StatusBadge status={blend.status} />
        </div>

        <dl className="mt-4 grid grid-cols-3 gap-4 text-sm">
          <div>
            <dt className="text-text-3">Style</dt>
            <dd className="mt-0.5 font-medium capitalize text-text">{blend.style ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-text-3">Version</dt>
            <dd className="mt-0.5 font-medium text-text">v{blend.version}</dd>
          </div>
          <div>
            <dt className="text-text-3">Daily usage</dt>
            <dd className="mt-0.5 font-medium text-text">
              {blend.daily_usage_kg != null ? `${blend.daily_usage_kg} kg` : "—"}
            </dd>
          </div>
        </dl>
      </div>

      {/* Recipe */}
      <div className="rounded-xl border border-border bg-surface p-6">
        <h2 className="mb-4 text-sm font-semibold text-text">Recipe</h2>

        {/* Stacked bar */}
        <div className="flex h-4 overflow-hidden rounded-full mb-4" role="img" aria-label="Recipe percentage bar">
          {blend.items.map((item, idx) => {
            const colors = ["bg-brand-500", "bg-brand-300", "bg-brand-700", "bg-brand-200", "bg-brand-800"];
            return (
              <div
                key={item.id}
                className={colors[idx % colors.length]}
                style={{ width: `${item.percentage}%` }}
                title={`${item.bean?.name ?? "Bean"}: ${item.percentage}%`}
              />
            );
          })}
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-3">
              <th className="pb-2 font-medium">Bean</th>
              <th className="pb-2 font-medium">Origin</th>
              <th className="pb-2 font-medium text-right">%</th>
            </tr>
          </thead>
          <tbody>
            {blend.items.map((item) => (
              <tr key={item.id} className="border-b border-border/50 last:border-0">
                <td className="py-2 pr-4">
                  {item.bean ? (
                    <Link
                      href={`/dashboard/owner/beans/${item.coffee_bean_id}`}
                      className="font-medium text-text hover:text-brand-600"
                    >
                      {item.bean.name}
                    </Link>
                  ) : (
                    <span className="text-text-3 italic">Bean not found</span>
                  )}
                </td>
                <td className="py-2 pr-4 text-text-3">{item.bean?.origin ?? "—"}</td>
                <td className="py-2 text-right font-semibold text-text">{item.percentage}%</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={2} className="pt-2 text-xs text-text-3">Total</td>
              <td className={`pt-2 text-right text-xs font-semibold ${totalPct === 100 ? "text-success" : "text-danger"}`}>
                {totalPct}%
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Flavor profile */}
      {computed && (
        <div className="rounded-xl border border-border bg-surface p-6">
          <h2 className="mb-4 text-sm font-semibold text-text">
            Flavor profile{" "}
            <span className="font-normal text-text-3">(weighted average of bean values)</span>
          </h2>
          <div className="flex flex-col gap-2">
            <FlavorBar label="Acidity" value={computed.acidity} />
            <FlavorBar label="Body" value={computed.body} />
            <FlavorBar label="Sweetness" value={computed.sweetness} />
          </div>
        </div>
      )}

      {/* Actions */}
      <BlendActions blend={blend} />

      {/* Feedback */}
      <div className="rounded-xl border border-border bg-surface p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-text">Feedback</h2>
          <span className="text-xs text-text-3">
            Adjusted using your previous feedback
          </span>
        </div>
        <FeedbackSection blendId={blend.id} />
      </div>
    </div>
  );
}
