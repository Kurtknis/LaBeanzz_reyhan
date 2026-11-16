"use client";

import { useState, useTransition } from "react";
import { submitFeedback, type FeedbackEntry, type BrewContext } from "@/lib/api/feedback";
import { ApiError } from "@/lib/api/client";

interface Props {
  blendId: string;
  onSubmitted: (entry: FeedbackEntry) => void;
}

const BREW_OPTIONS: { value: BrewContext; label: string }[] = [
  { value: "espresso", label: "Espresso" },
  { value: "milk",     label: "Milk drink" },
  { value: "filter",   label: "Filter" },
];

const RATING_FIELDS: { key: keyof RatingFields; label: string }[] = [
  { key: "overall",   label: "Overall" },
  { key: "flavor",    label: "Flavor" },
  { key: "body",      label: "Body" },
  { key: "acidity",   label: "Acidity" },
  { key: "sweetness", label: "Sweetness" },
];

interface RatingFields {
  overall:   number;
  flavor:    number;
  body:      number;
  acidity:   number;
  sweetness: number;
}

function StarRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
}) {
  const [hover, setHover] = useState(0);
  const active = hover || value;

  return (
    <div className="flex items-center gap-4">
      <span className="w-20 shrink-0 text-sm text-text-2">{label}</span>
      <div className="flex gap-1" role="group" aria-label={`${label} rating`}>
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            onMouseEnter={() => setHover(star)}
            onMouseLeave={() => setHover(0)}
            aria-label={`${star} out of 5`}
            aria-pressed={value === star}
            className={`text-xl leading-none transition-colors ${
              star <= active ? "text-brand-400" : "text-surface-3"
            }`}
          >
            ★
          </button>
        ))}
      </div>
      {value > 0 && (
        <span className="text-xs text-text-3">{value}/5</span>
      )}
    </div>
  );
}

export function FeedbackForm({ blendId, onSubmitted }: Props) {
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const [brewContext, setBrewContext] = useState<BrewContext>("espresso");
  const [comment, setComment] = useState("");
  const [ratings, setRatings] = useState<RatingFields>({
    overall: 0, flavor: 0, body: 0, acidity: 0, sweetness: 0,
  });

  function setRating(key: keyof RatingFields, val: number) {
    setRatings((prev) => ({ ...prev, [key]: val }));
  }

  const allRated = Object.values(ratings).every((v) => v > 0);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!allRated || isPending) return;
    setError(null);

    startTransition(async () => {
      try {
        const entry = await submitFeedback(blendId, {
          ...ratings,
          brew_context: brewContext,
          comment: comment.trim() || undefined,
        });
        setSubmitted(true);
        onSubmitted(entry);
      } catch (err) {
        if (err instanceof ApiError) {
          const body = err.body as { error?: string };
          setError(body?.error ?? "Could not submit feedback.");
        } else {
          setError("Something went wrong.");
        }
      }
    });
  }

  if (submitted) {
    return (
      <div className="rounded-xl border border-success/30 bg-success/5 p-5 text-sm text-success">
        ✓ Feedback saved. The next blend you generate may reflect this rating.
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      {/* Brew context */}
      <div>
        <span className="mb-2 block text-sm font-medium text-text">
          How did you brew it?
        </span>
        <div className="flex gap-2">
          {BREW_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setBrewContext(opt.value)}
              className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                brewContext === opt.value
                  ? "border-brand-500 bg-brand-50 text-brand-700"
                  : "border-border text-text-2 hover:bg-surface-2"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Star ratings */}
      <div>
        <span className="mb-3 block text-sm font-medium text-text">Ratings</span>
        <div className="flex flex-col gap-2.5">
          {RATING_FIELDS.map(({ key, label }) => (
            <StarRow
              key={key}
              label={label}
              value={ratings[key]}
              onChange={(v) => setRating(key, v)}
            />
          ))}
        </div>
      </div>

      {/* Comment */}
      <label className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-text">
          Comment{" "}
          <span className="font-normal text-text-3">(optional)</span>
        </span>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          maxLength={2000}
          rows={3}
          placeholder="e.g. Great body, but too acidic for milk drinks…"
          className="resize-none rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-3 focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <span className="text-xs text-text-3">
          Comments are used to personalise future blend suggestions.
        </span>
      </label>

      {error && (
        <p className="text-sm text-danger">{error}</p>
      )}

      <button
        type="submit"
        disabled={!allRated || isPending}
        className="self-start rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isPending ? "Saving…" : "Submit feedback"}
      </button>
    </form>
  );
}
