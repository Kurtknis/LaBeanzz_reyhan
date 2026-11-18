import Link from "next/link";
import { auth } from "@/auth";
import { getDashboardSummary, type DashboardSummary } from "@/lib/api/insights";
import { ReorderCard } from "@/components/features/ReorderCard";
import { ProducerSpotlight } from "@/components/features/ProducerSpotlight";
import { StatTile } from "@/components/ui/StatTile";
import { formatMonth, formatPrice, UNITS } from "@/product.config";

export const instant = false;

const QUICK_LINKS = [
  { title: "New blend", description: "Describe a flavor and get an AI recipe.", href: "/dashboard/owner/blends/new", icon: "✨" },
  { title: "My blends", description: "View and manage your saved recipes.", href: "/dashboard/owner/blends", icon: "☕" },
  { title: "Browse beans", description: "Explore the catalog from all suppliers.", href: "/dashboard/owner/beans", icon: "🌱" },
  { title: "AI Lab", description: "Ask questions and analyse your feedback.", href: "/dashboard/owner/ai-lab", icon: "🧪" },
];

export default async function OwnerDashboardPage() {
  const session = await auth();

  let summary: DashboardSummary | null = null;
  try {
    summary = await getDashboardSummary();
  } catch {
    summary = null;
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">
          Welcome back{session?.user?.name ? `, ${session.user.name}` : ""}.
        </h1>
        <p className="mt-1 text-sm text-text-3">Here&apos;s what&apos;s happening with your coffee operation.</p>
      </div>

      {summary === null ? (
        <div role="alert" className="rounded-xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger">
          Your dashboard figures could not be loaded. Refresh the page to try again.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label="Open orders" value={String(summary.active_orders)} href="/dashboard/owner/orders" />
            <StatTile label="Active blends" value={String(summary.active_blends)} href="/dashboard/owner/blends" />
            <StatTile
              label={`Ordered in ${formatMonth(summary.month)}`}
              value={`${summary.month_kg} ${UNITS.weight}`}
              href="/dashboard/owner/insights"
            />
            <StatTile
              label={`Spend in ${formatMonth(summary.month)}`}
              value={formatPrice(summary.month_spend)}
              href="/dashboard/owner/insights"
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ReorderCard items={summary.reorder} />
            <ProducerSpotlight spotlight={summary.spotlight} />
          </div>
        </>
      )}

      <div>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-text-3">Quick actions</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {QUICK_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="flex items-start gap-3 rounded-xl border border-border bg-surface p-4 transition-shadow hover:shadow-md"
            >
              <span className="text-xl" aria-hidden="true">{link.icon}</span>
              <div>
                <p className="font-medium text-text">{link.title}</p>
                <p className="mt-0.5 text-sm text-text-3">{link.description}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
