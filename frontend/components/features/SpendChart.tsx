"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatMonth } from "@/product.config";

interface SpendChartProps {
  data: { month: string; value: number }[];
  /** Formats axis ticks and the tooltip, e.g. a currency or "12 kg" */
  format: (value: number) => string;
  label: string;
}

export function SpendChart({ data, format, label }: SpendChartProps) {
  const hasData = data.some((d) => d.value > 0);
  if (!hasData) {
    return (
      <div className="flex h-56 items-center justify-center rounded-lg bg-surface-2 text-sm text-text-3">
        No orders in this period yet.
      </div>
    );
  }

  const rows = data.map((d) => ({ ...d, name: formatMonth(d.month) }));

  return (
    <div className="h-56 w-full" role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--color-border)" />
          <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "var(--color-text-3)" }} />
          <YAxis
            tickLine={false}
            axisLine={false}
            width={64}
            tick={{ fontSize: 12, fill: "var(--color-text-3)" }}
            tickFormatter={(v: number) => format(v)}
          />
          <Tooltip
            cursor={{ fill: "var(--color-surface-2)" }}
            formatter={(v) => [format(Number(v)), label]}
            contentStyle={{ borderRadius: 8, border: "1px solid var(--color-border)", fontSize: 12 }}
          />
          <Bar dataKey="value" fill="var(--color-brand-500)" radius={[4, 4, 0, 0]} maxBarSize={48} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
