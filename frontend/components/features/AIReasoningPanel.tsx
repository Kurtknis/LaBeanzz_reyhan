"use client";

import type { BlendDraft } from "@/lib/api/ai";
import { FLAVOR_AXES } from "@/product.config";

interface Props {
  draft: BlendDraft;
}

function ProfileMeter({
  label,
  value,
  max = 10,
}: {
  label: string;
  value: number;
  max?: number;
}) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-text-2">{label}</span>
        <span className="text-xs font-semibold text-text">{value.toFixed(1)}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-3">
        <div
          className="h-2 rounded-full bg-brand-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function EstimatedNote({ label, value }: { label: string; value: number }) {
  const filled = Math.round(value);
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-xs text-text-3 w-20 shrink-0">{label}</span>
      <div className="flex gap-0.5">
        {Array.from({ length: 10 }).map((_, i) => (
          <span
            key={i}
            className={`inline-block h-2 w-2 rounded-sm ${
              i < filled ? "bg-brand-400" : "bg-surface-3"
            }`}
          />
        ))}
      </div>
      <span className="text-xs text-text-3 w-6 text-right">{value.toFixed(1)}</span>
    </div>
  );
}

export function AIReasoningPanel({ draft }: Props) {
  const { profile, reasoning, applied_feedback } = draft;

  return (
    <div className="flex flex-col gap-6">
      {/* Computed profile */}
      <section>
        <h3 className="mb-3 text-sm font-semibold text-text">
          Computed profile
          <span className="ml-2 text-xs font-normal text-text-3">
            (weighted average of bean values)
          </span>
        </h3>
        <div className="flex flex-col gap-2.5">
          {FLAVOR_AXES.map((axis) => (
            <ProfileMeter
              key={axis.key}
              label={axis.label}
              value={profile.computed[axis.key as keyof typeof profile.computed]}
            />
          ))}
        </div>
      </section>

      {/* Estimated tasting notes */}
      <section>
        <h3 className="mb-3 text-sm font-semibold text-text">
          Estimated notes
          <span className="ml-2 text-xs font-normal text-text-3">
            (AI estimate — directional only)
          </span>
        </h3>
        <div className="flex flex-col gap-2">
          <EstimatedNote label="Chocolate" value={profile.estimated.chocolate} />
          <EstimatedNote label="Caramel"   value={profile.estimated.caramel}   />
          <EstimatedNote label="Fruitiness" value={profile.estimated.fruitiness} />
          <EstimatedNote label="Nuttiness" value={profile.estimated.nuttiness}  />
          <EstimatedNote label="Florality" value={profile.estimated.florality}  />
        </div>
      </section>

      {/* Applied feedback */}
      {applied_feedback.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold text-text">
            Adjusted using your previous feedback
          </h3>
          <ul className="flex flex-col gap-1.5">
            {applied_feedback.map((item, i) => (
              <li
                key={i}
                className="flex items-start gap-2 rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-800"
              >
                <span className="mt-0.5 shrink-0">↻</span>
                {item}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Reasoning */}
      <section>
        <h3 className="mb-2 text-sm font-semibold text-text">Why this blend</h3>
        <p className="text-sm leading-relaxed text-text-2">{reasoning}</p>
      </section>
    </div>
  );
}
