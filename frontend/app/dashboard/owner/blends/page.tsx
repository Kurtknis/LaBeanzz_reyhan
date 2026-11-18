"use client";

import { useState, useEffect, useCallback, useTransition } from "react";
import Link from "next/link";
import { getBlends, duplicateBlend, setBlendStatus, type Blend } from "@/lib/api/blends";
import { BLEND_STATUS, type BlendStatus } from "@/product.config";
import { FlavorBar } from "@/components/ui/FlavorBar";

const STATUS_FILTERS: { value: BlendStatus | ""; label: string }[] = [
  { value: "", label: "All" },
  { value: "DRAFT", label: "Draft" },
  { value: "ACTIVE", label: "Active" },
  { value: "ARCHIVED", label: "Archived" },
];

function BlendStatusBadge({ status }: { status: BlendStatus }) {
  const config = BLEND_STATUS[status];
  const colors: Record<BlendStatus, string> = {
    DRAFT: "bg-info/10 text-info",
    ACTIVE: "bg-success/10 text-success",
    ARCHIVED: "bg-surface-3 text-text-3",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status]}`}>
      {config.label}
    </span>
  );
}

export default function MyBlendsPage() {
  const [blends, setBlends] = useState<Blend[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<BlendStatus | "">("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [isPending, startTransition] = useTransition();

  const fetchBlends = useCallback(async (status: BlendStatus | "", p: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getBlends({ status: status || undefined, page: p });
      setBlends(data.items);
      setTotal(data.total);
      setPages(data.pages);
    } catch {
      setError("Could not load blends.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchBlends(statusFilter, page); }, [fetchBlends, statusFilter, page]);

  function handleDuplicate(id: string) {
    startTransition(async () => {
      try {
        const copy = await duplicateBlend(id);
        setBlends((prev) => [copy, ...prev]);
        setTotal((t) => t + 1);
      } catch {
        alert("Could not duplicate blend.");
      }
    });
  }

  function handleArchive(id: string) {
    startTransition(async () => {
      try {
        const updated = await setBlendStatus(id, { status: "ARCHIVED" });
        setBlends((prev) => prev.map((b) => b.id === id ? updated : b));
      } catch (err: unknown) {
        const body = (err as { body?: { error?: string } }).body;
        alert(body?.error ?? "Could not archive blend.");
      }
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text">My Blends</h1>
          <p className="mt-1 text-sm text-text-3">{total} blend{total === 1 ? "" : "s"}</p>
        </div>
        <Link
          href="/dashboard/owner/blends/new"
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600"
        >
          + New blend
        </Link>
      </div>

      {/* Status filter */}
      <div className="flex gap-2 flex-wrap">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => { setStatusFilter(f.value as BlendStatus | ""); setPage(1); }}
            className={`rounded-full px-3 py-1 text-sm transition-colors ${
              statusFilter === f.value
                ? "bg-brand-500 text-white"
                : "border border-border text-text-2 hover:bg-surface-2"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && <div className="py-16 text-center text-sm text-text-3">Loading…</div>}
      {error && <div className="rounded-xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger">{error}</div>}

      {!loading && !error && blends.length === 0 && (
        <div className="rounded-xl border border-border bg-surface p-12 text-center">
          <p className="text-text-3">No blends yet.</p>
          <Link href="/dashboard/owner/blends/new" className="mt-4 inline-block text-sm text-brand-600 hover:underline">
            Generate your first blend →
          </Link>
        </div>
      )}

      {!loading && !error && blends.length > 0 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {blends.map((blend) => (
            <div key={blend.id} className="rounded-xl border border-border bg-surface p-5 flex flex-col gap-4">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <Link
                    href={`/dashboard/owner/blends/${blend.id}`}
                    className="font-semibold text-text hover:text-brand-600 line-clamp-1"
                  >
                    {blend.name}
                  </Link>
                  {blend.description && (
                    <p className="mt-0.5 text-sm text-text-3 line-clamp-1">{blend.description}</p>
                  )}
                </div>
                <BlendStatusBadge status={blend.status} />
              </div>

              {/* Recipe preview */}
              {blend.items.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {blend.items.map((item) => (
                    <span
                      key={item.id}
                      className="rounded-full bg-surface-2 px-2.5 py-0.5 text-xs text-text-2"
                    >
                      {item.bean?.name ?? "Unknown"} {item.percentage}%
                    </span>
                  ))}
                </div>
              )}

              {blend.items.some((i) => i.bean && !["AVAILABLE", "LOW_STOCK"].includes(i.bean.status)) && (
                <p className="rounded-lg bg-warning/10 px-3 py-2 text-xs text-warning">
                  A bean in this blend is unavailable. Open it to find a substitute.
                </p>
              )}

              {/* Flavor profile */}
              {blend.predicted_profile?.computed && (
                <div className="flex flex-col gap-1.5">
                  <FlavorBar label="Acidity" value={blend.predicted_profile.computed.acidity} />
                  <FlavorBar label="Body" value={blend.predicted_profile.computed.body} />
                  <FlavorBar label="Sweetness" value={blend.predicted_profile.computed.sweetness} />
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-3 pt-1 border-t border-border mt-auto">
                <Link
                  href={`/dashboard/owner/blends/${blend.id}`}
                  className="text-xs text-brand-600 hover:underline"
                >
                  View
                </Link>
                <Link
                  href={`/dashboard/owner/blends/${blend.id}/edit`}
                  className="text-xs text-text-3 hover:text-text"
                >
                  Edit
                </Link>
                <button
                  onClick={() => handleDuplicate(blend.id)}
                  disabled={isPending}
                  className="text-xs text-text-3 hover:text-text disabled:opacity-40"
                >
                  Duplicate
                </button>
                {blend.status !== "ARCHIVED" && (
                  <button
                    onClick={() => handleArchive(blend.id)}
                    disabled={isPending}
                    className="ml-auto text-xs text-text-3 hover:text-danger disabled:opacity-40"
                  >
                    Archive
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-40">Previous</button>
          <span className="text-sm text-text-3">{page} / {pages}</span>
          <button disabled={page >= pages} onClick={() => setPage((p) => p + 1)} className="rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-40">Next</button>
        </div>
      )}
    </div>
  );
}
