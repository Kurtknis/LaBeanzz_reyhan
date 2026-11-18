import Link from "next/link";
import type { Spotlight } from "@/lib/api/insights";

export function ProducerSpotlight({ spotlight }: { spotlight: Spotlight | null }) {
  if (!spotlight) return null;
  const { bean, supplier } = spotlight;
  const place = [bean.farm, bean.region, bean.origin].filter(Boolean).join(", ");

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-text-3">Producer spotlight</p>
      <h2 className="mt-2 text-lg font-semibold text-text">{bean.name}</h2>
      <p className="mt-0.5 text-sm text-text-3">
        {place}
        {bean.producer ? ` · ${bean.producer}` : ""}
      </p>
      <p className="mt-3 text-sm leading-relaxed text-text-2">{bean.producer_story}</p>
      <div className="mt-4 flex flex-wrap items-center gap-4 text-sm">
        <Link href={`/dashboard/owner/beans/${bean.id}`} className="text-brand-600 hover:underline">
          View bean →
        </Link>
        {supplier.business_name && (
          <Link href={`/dashboard/owner/suppliers/${supplier.id}`} className="text-text-3 hover:text-text">
            {supplier.business_name}
          </Link>
        )}
      </div>
    </div>
  );
}
