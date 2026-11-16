"use client";

import { useState, useEffect } from "react";
import { getFeedback, type FeedbackEntry } from "@/lib/api/feedback";

interface Props {
  blendId: string;
  /** Additional entries submitted in the same session without a full reload */
  newEntries?: FeedbackEntry[];
}

function Stars({ value }: { value: number }) {
  return (
    <span className="text-sm text-brand-400" aria-label={`${value} out of 5`}>
      {"★".repeat(value)}
      <span className="text-surface-3">{"★".repeat(5 - value)}</span>
    </span>
  );
}

function RatingRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-text-3">{label}</span>
      <Stars value={value} />
    </div>
  );
}

export function FeedbackList({ blendId, newEntries = [] }: Props) {
  const [entries, setEntries] = useState<FeedbackEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getFeedback(blendId)
      .then((r) => setEntries(r.items))
      .catch(() => setError("Could not load feedback."))
      .finally(() => setLoading(false));
  }, [blendId]);

  // Merge newly submitted entries (deduplicate by id)
  const existingIds = new Set(entries.map((e) => e.id));
  const all = [
    ...newEntries.filter((e) => !existingIds.has(e.id)),
    ...entries,
  ];

  if (loading) {
    return <p className="text-sm text-text-3">Loading…</p>;
  }
  if (error) {
    return <p className="text-sm text-danger">{error}</p>;
  }
  if (all.length === 0) {
    return (
      <p className="text-sm text-text-3">
        No feedback yet. Submit your first rating above.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {all.map((entry) => (
        <div
          key={entry.id}
          className="rounded-xl border border-border bg-surface p-4"
        >
          <div className="mb-3 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Stars value={entry.overall} />
              <span className="text-xs text-text-3 capitalize">
                {entry.brew_context}
              </span>
            </div>
            <span className="text-xs text-text-3">
              {new Date(entry.created_at).toLocaleDateString()}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-x-6 gap-y-1 mb-3">
            <RatingRow label="Flavor"    value={entry.flavor}    />
            <RatingRow label="Body"      value={entry.body}      />
            <RatingRow label="Acidity"   value={entry.acidity}   />
            <RatingRow label="Sweetness" value={entry.sweetness} />
          </div>

          {entry.comment && (
            <p className="text-sm leading-relaxed text-text-2 italic">
              "{entry.comment}"
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
