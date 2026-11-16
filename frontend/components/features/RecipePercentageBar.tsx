"use client";

import type { RecipeItem } from "@/lib/api/ai";

// 12 distinct colours that work on both light and dark surfaces
const SLICE_COLORS = [
  "#c47f27", // brand-500
  "#2d7a4f", // success
  "#1d6fa4", // info
  "#b45309", // warning
  "#7c3aed", // purple
] as const;

interface Props {
  recipe: RecipeItem[];
}

export function RecipePercentageBar({ recipe }: Props) {
  if (!recipe.length) return null;

  return (
    <div className="flex flex-col gap-3">
      {/* Stacked bar */}
      <div className="flex h-5 w-full overflow-hidden rounded-full border border-border">
        {recipe.map((item, i) => (
          <div
            key={item.coffee_bean_id}
            style={{
              width: `${item.percentage}%`,
              backgroundColor: SLICE_COLORS[i % SLICE_COLORS.length],
            }}
            title={`${item.name} — ${item.percentage}%`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5">
        {recipe.map((item, i) => (
          <div key={item.coffee_bean_id} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: SLICE_COLORS[i % SLICE_COLORS.length] }}
            />
            <span className="text-xs text-text-2">
              {item.name}
              <span className="ml-1 font-semibold text-text">
                {item.percentage}%
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
