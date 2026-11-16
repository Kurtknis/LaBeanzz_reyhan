"use client";

import { useState } from "react";
import { FeedbackForm } from "./FeedbackForm";
import { FeedbackList } from "./FeedbackList";
import type { FeedbackEntry } from "@/lib/api/feedback";

interface Props {
  blendId: string;
}

export function FeedbackSection({ blendId }: Props) {
  const [newEntries, setNewEntries] = useState<FeedbackEntry[]>([]);
  const [showForm, setShowForm] = useState(false);

  function handleSubmitted(entry: FeedbackEntry) {
    setNewEntries((prev) => [entry, ...prev]);
    setShowForm(false);
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Past feedback */}
      <FeedbackList blendId={blendId} newEntries={newEntries} />

      {/* Toggle form */}
      {!showForm ? (
        <button
          onClick={() => setShowForm(true)}
          className="self-start rounded-lg border border-border px-4 py-2 text-sm text-text-2 hover:bg-surface-2"
        >
          + Add feedback
        </button>
      ) : (
        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-text">New feedback</h3>
            <button
              onClick={() => setShowForm(false)}
              className="text-xs text-text-3 hover:text-text"
            >
              Cancel
            </button>
          </div>
          <FeedbackForm blendId={blendId} onSubmitted={handleSubmitted} />
        </div>
      )}
    </div>
  );
}
