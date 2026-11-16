"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { setBlendStatus, duplicateBlend, type Blend } from "@/lib/api/blends";
import type { BlendStatus } from "@/product.config";

interface Props {
  blend: Blend;
}

export function BlendActions({ blend }: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [dailyUsage, setDailyUsage] = useState("");
  const [showActivate, setShowActivate] = useState(false);

  function transition(status: BlendStatus, dailyUsageKg?: number) {
    setError(null);
    startTransition(async () => {
      try {
        await setBlendStatus(blend.id, {
          status,
          daily_usage_kg: dailyUsageKg,
        });
        router.refresh();
      } catch (err: unknown) {
        const body = (err as { body?: { error?: string } }).body;
        setError(body?.error ?? "Could not update status.");
      }
    });
  }

  function handleActivate() {
    const kg = parseFloat(dailyUsage);
    if (!kg || kg <= 0) {
      setError("Enter a daily usage in kg before activating.");
      return;
    }
    transition("ACTIVE", kg);
    setShowActivate(false);
  }

  function handleDuplicate() {
    startTransition(async () => {
      const copy = await duplicateBlend(blend.id);
      router.push(`/dashboard/owner/blends/${copy.id}`);
    });
  }

  return (
    <div className="rounded-xl border border-border bg-surface-2 p-5 flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-text">Actions</h2>

      {error && (
        <p className="text-sm text-danger">{error}</p>
      )}

      <div className="flex flex-wrap gap-2">
        <Link
          href={`/dashboard/owner/blends/${blend.id}/edit`}
          className="rounded-lg border border-border px-4 py-2 text-sm text-text-2 hover:bg-surface"
        >
          Edit recipe
        </Link>

        <button
          onClick={handleDuplicate}
          disabled={isPending}
          className="rounded-lg border border-border px-4 py-2 text-sm text-text-2 hover:bg-surface disabled:opacity-40"
        >
          Duplicate
        </button>

        {blend.status === "DRAFT" && !showActivate && (
          <button
            onClick={() => setShowActivate(true)}
            disabled={isPending}
            className="rounded-lg bg-success/10 border border-success/20 px-4 py-2 text-sm text-success hover:bg-success/20 disabled:opacity-40"
          >
            Activate
          </button>
        )}

        {blend.status === "DRAFT" && showActivate && (
          <div className="flex items-center gap-2 w-full">
            <input
              type="number"
              min={0.1}
              step={0.1}
              value={dailyUsage}
              onChange={(e) => setDailyUsage(e.target.value)}
              placeholder="Daily usage (kg)"
              className="rounded-lg border border-border bg-surface px-3 py-2 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <button
              onClick={handleActivate}
              disabled={isPending}
              className="rounded-lg bg-success px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {isPending ? "Activating…" : "Confirm activate"}
            </button>
            <button
              onClick={() => setShowActivate(false)}
              className="text-sm text-text-3 hover:text-text"
            >
              Cancel
            </button>
          </div>
        )}

        {blend.status === "ACTIVE" && (
          <button
            onClick={() => transition("ARCHIVED")}
            disabled={isPending}
            className="rounded-lg border border-border px-4 py-2 text-sm text-text-3 hover:bg-surface disabled:opacity-40"
          >
            Archive
          </button>
        )}

        {blend.status === "ARCHIVED" && (
          <button
            onClick={() => transition("ACTIVE")}
            disabled={isPending}
            className="rounded-lg border border-border px-4 py-2 text-sm text-text-2 hover:bg-surface disabled:opacity-40"
          >
            Reactivate
          </button>
        )}
      </div>
    </div>
  );
}
