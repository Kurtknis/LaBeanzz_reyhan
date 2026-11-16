"use client";

import { useState, useEffect, useTransition } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { getBlend, patchBlend } from "@/lib/api/blends";
import { getBeans, type CoffeeBean } from "@/lib/api/beans";
import { BlendRecipeEditor, type RecipeRow } from "@/components/features/BlendRecipeEditor";
import { ApiError } from "@/lib/api/client";

export default function EditBlendPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [availableBeans, setAvailableBeans] = useState<CoffeeBean[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [style, setStyle] = useState<"espresso" | "filter" | "milk">("espresso");
  const [rows, setRows] = useState<RecipeRow[]>([]);
  const [isPending, startTransition] = useTransition();
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [blend, beansData] = await Promise.all([
          getBlend(id),
          getBeans({ status: "AVAILABLE", per_page: 100 }),
        ]);
        setName(blend.name);
        setDescription(blend.description ?? "");
        setStyle((blend.style ?? "espresso") as "espresso" | "filter" | "milk");
        setRows(
          blend.items.map((item) => ({
            coffee_bean_id: item.coffee_bean_id,
            name: item.bean?.name ?? "Unknown",
            origin: item.bean?.origin ?? "",
            percentage: item.percentage,
          }))
        );
        setAvailableBeans(beansData.items);
      } catch (err) {
        setLoadError(err instanceof Error ? err.message : "Failed to load blend.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const total = rows.reduce((s, r) => s + r.percentage, 0);
  const canSave = name.trim().length > 0 && rows.length >= 2 && rows.length <= 5 && total === 100 && !isPending;

  function handleSave() {
    if (!canSave) return;
    setSaveError(null);
    startTransition(async () => {
      try {
        await patchBlend(id, {
          name: name.trim(),
          description: description.trim() || undefined,
          style,
          items: rows.map((r) => ({ coffee_bean_id: r.coffee_bean_id, percentage: r.percentage })),
        });
        router.push(`/dashboard/owner/blends/${id}`);
        router.refresh();
      } catch (err) {
        if (err instanceof ApiError) {
          const body = err.body as { error?: string | object[] };
          setSaveError(typeof body?.error === "string" ? body.error : "Save failed.");
        } else {
          setSaveError("Something went wrong. Please try again.");
        }
      }
    });
  }

  if (loading) return <div className="py-16 text-center text-sm text-text-3">Loading…</div>;
  if (loadError) return <div className="text-sm text-danger p-4">{loadError}</div>;

  return (
    <div className="mx-auto max-w-2xl flex flex-col gap-6">
      <div className="flex items-center gap-2 text-xs text-text-3">
        <Link href="/dashboard/owner/blends" className="hover:text-text">My Blends</Link>
        <span>/</span>
        <Link href={`/dashboard/owner/blends/${id}`} className="hover:text-text truncate">{name}</Link>
        <span>/</span>
        <span>Edit</span>
      </div>

      <div>
        <h1 className="text-xl font-semibold text-text">Edit blend</h1>
        <p className="mt-1 text-sm text-text-3">Editing the recipe bumps the version number.</p>
      </div>

      <div className="rounded-xl border border-border bg-surface p-5 flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-text">Blend name *</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={200}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-3 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-text">Description</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={2000}
            rows={2}
            className="resize-none rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </label>

        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-text">Brew style</span>
          <div className="flex gap-2">
            {(["espresso", "milk", "filter"] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setStyle(s)}
                className={`rounded-lg border px-3 py-1.5 text-sm capitalize transition-colors ${
                  style === s ? "border-brand-500 bg-brand-50 text-brand-700" : "border-border text-text-2 hover:bg-surface-2"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface p-5">
        <h2 className="mb-4 text-sm font-semibold text-text">Recipe</h2>
        <BlendRecipeEditor initial={rows} availableBeans={availableBeans} onChange={setRows} />
      </div>

      {saveError && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 p-3 text-sm text-danger">{saveError}</div>
      )}

      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={!canSave}
          className="rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPending ? "Saving…" : "Save changes"}
        </button>
        <Link
          href={`/dashboard/owner/blends/${id}`}
          className="rounded-lg border border-border px-5 py-2.5 text-sm text-text-2 hover:text-text"
        >
          Cancel
        </Link>
      </div>
    </div>
  );
}
