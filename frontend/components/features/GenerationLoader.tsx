"use client";

import { useEffect, useState } from "react";

const STAGES = [
  { key: "retrieving", label: "Retrieving coffee knowledge…" },
  { key: "selecting",  label: "Selecting candidate beans…"   },
  { key: "generating", label: "Building your recipe…"        },
  { key: "validating", label: "Validating the blend…"        },
] as const;

interface Props {
  /** Pass true while the fetch is in flight. */
  active: boolean;
}

export function GenerationLoader({ active }: Props) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (!active) {
      setStage(0);
      return;
    }
    // Advance through stages every ~2 s while loading
    const id = setInterval(() => {
      setStage((s) => (s < STAGES.length - 1 ? s + 1 : s));
    }, 2000);
    return () => clearInterval(id);
  }, [active]);

  if (!active) return null;

  return (
    <div className="flex flex-col items-center gap-6 py-12 text-center">
      {/* Spinning ring */}
      <div
        className="h-12 w-12 animate-spin rounded-full border-4 border-brand-200 border-t-brand-500"
        aria-hidden="true"
      />

      {/* Stage list */}
      <ol className="flex flex-col gap-2">
        {STAGES.map((s, i) => {
          const done    = i < stage;
          const current = i === stage;
          return (
            <li
              key={s.key}
              className={`text-sm transition-opacity ${
                done
                  ? "text-text-3 line-through opacity-60"
                  : current
                  ? "font-medium text-brand-600"
                  : "text-text-3 opacity-40"
              }`}
            >
              {done ? "✓ " : current ? "→ " : "  "}
              {s.label}
            </li>
          );
        })}
      </ol>

      <p className="text-xs text-text-3">
        This usually takes 10–20 seconds.
      </p>
    </div>
  );
}
