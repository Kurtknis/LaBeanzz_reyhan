import Link from "next/link";

interface StatTileProps {
  label: string;
  value: string;
  hint?: string;
  href?: string;
}

export function StatTile({ label, value, hint, href }: StatTileProps) {
  const body = (
    <>
      <p className="text-xs font-medium uppercase tracking-wide text-text-3">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-text tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-xs text-text-3">{hint}</p>}
    </>
  );
  const base = "rounded-xl border border-border bg-surface p-5";

  return href ? (
    <Link href={href} className={`${base} transition-shadow hover:shadow-md`}>
      {body}
    </Link>
  ) : (
    <div className={base}>{body}</div>
  );
}
