"use client";

import { useState, useEffect, useCallback, useTransition } from "react";
import {
  getPresets,
  createPreset,
  deletePreset,
  type Preset,
  type CreatePresetPayload,
} from "@/lib/api/presets";
import { ROAST_LEVELS } from "@/product.config";

const STYLES = [
  { value: "espresso", label: "Espresso" },
  { value: "milk", label: "Milk drinks" },
  { value: "filter", label: "Filter" },
] as const;

function RatingInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-text-3">{label} (0–10)</span>
      <input
        type="number"
        min={0}
        max={10}
        step={0.1}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="—"
        className="w-20 rounded-lg border border-border bg-surface px-2 py-1.5 text-sm text-text focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
    </label>
  );
}

export default function PresetsPage() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [showForm, setShowForm] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [fields, setFields] = useState({
    name: "",
    coffee_style: "" as "" | "espresso" | "milk" | "filter",
    acidity_pref: "",
    body_pref: "",
    sweetness_pref: "",
    brewing_method: "",
    notes: "",
  });

  const fetchPresets = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getPresets();
      setPresets(data.items);
    } catch {
      setError("Could not load presets.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPresets(); }, [fetchPresets]);

  function set(key: keyof typeof fields, value: string) {
    setFields((prev) => ({ ...prev, [key]: value }));
  }

  function handleCreate() {
    if (!fields.name.trim()) { setFormError("Name is required."); return; }
    setFormError(null);

    startTransition(async () => {
      const payload: CreatePresetPayload = {
        name: fields.name.trim(),
        coffee_style: (fields.coffee_style || undefined) as CreatePresetPayload["coffee_style"],
        acidity_pref: fields.acidity_pref ? parseFloat(fields.acidity_pref) : undefined,
        body_pref: fields.body_pref ? parseFloat(fields.body_pref) : undefined,
        sweetness_pref: fields.sweetness_pref ? parseFloat(fields.sweetness_pref) : undefined,
        brewing_method: fields.brewing_method.trim() || undefined,
        notes: fields.notes.trim() || undefined,
      };

      try {
        const preset = await createPreset(payload);
        setPresets((prev) => [...prev, preset]);
        setShowForm(false);
        setFields({ name: "", coffee_style: "", acidity_pref: "", body_pref: "", sweetness_pref: "", brewing_method: "", notes: "" });
      } catch (err: unknown) {
        const body = (err as { body?: { error?: string } }).body;
        setFormError(body?.error ?? "Could not create preset.");
      }
    });
  }

  function handleDelete(id: string, name: string) {
    if (!confirm(`Delete preset "${name}"?`)) return;
    startTransition(async () => {
      try {
        await deletePreset(id);
        setPresets((prev) => prev.filter((p) => p.id !== id));
      } catch {
        alert("Could not delete preset.");
      }
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text">Presets</h1>
          <p className="mt-1 text-sm text-text-3">
            Save your preferred flavor targets to speed up blend generation.
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600"
        >
          {showForm ? "Cancel" : "+ New preset"}
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="rounded-xl border border-border bg-surface p-5 flex flex-col gap-4">
          <h2 className="text-sm font-semibold text-text">New preset</h2>

          {formError && (
            <p className="text-sm text-danger">{formError}</p>
          )}

          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-text-3">Name *</span>
            <input
              value={fields.name}
              onChange={(e) => set("name", e.target.value)}
              maxLength={100}
              placeholder="e.g. My daily espresso"
              className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-3 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </label>

          <div className="flex flex-col gap-1.5">
            <span className="text-xs text-text-3">Coffee style</span>
            <div className="flex gap-2 flex-wrap">
              {STYLES.map((s) => (
                <button
                  key={s.value}
                  type="button"
                  onClick={() => set("coffee_style", fields.coffee_style === s.value ? "" : s.value)}
                  className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                    fields.coffee_style === s.value
                      ? "border-brand-500 bg-brand-50 text-brand-700"
                      : "border-border text-text-2 hover:bg-surface-2"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-4 flex-wrap">
            <RatingInput label="Acidity" value={fields.acidity_pref} onChange={(v) => set("acidity_pref", v)} />
            <RatingInput label="Body" value={fields.body_pref} onChange={(v) => set("body_pref", v)} />
            <RatingInput label="Sweetness" value={fields.sweetness_pref} onChange={(v) => set("sweetness_pref", v)} />
          </div>

          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-text-3">Notes</span>
            <textarea
              rows={2}
              value={fields.notes}
              onChange={(e) => set("notes", e.target.value)}
              maxLength={2000}
              placeholder="Any additional preferences…"
              className="resize-none rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-3 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </label>

          <div className="flex gap-3">
            <button
              onClick={handleCreate}
              disabled={isPending}
              className="rounded-lg bg-brand-500 px-5 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-50"
            >
              {isPending ? "Saving…" : "Create preset"}
            </button>
          </div>
        </div>
      )}

      {loading && <div className="py-16 text-center text-sm text-text-3">Loading…</div>}
      {error && <div className="text-sm text-danger">{error}</div>}

      {!loading && !error && presets.length === 0 && !showForm && (
        <div className="rounded-xl border border-border bg-surface p-12 text-center">
          <p className="text-text-3">No presets yet.</p>
          <button
            onClick={() => setShowForm(true)}
            className="mt-4 inline-block text-sm text-brand-600 hover:underline"
          >
            Create your first preset →
          </button>
        </div>
      )}

      {!loading && presets.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {presets.map((p) => (
            <div key={p.id} className="rounded-xl border border-border bg-surface p-4 flex flex-col gap-3">
              <div className="flex items-start justify-between gap-2">
                <p className="font-semibold text-text">{p.name}</p>
                {p.coffee_style && (
                  <span className="rounded-full bg-surface-2 px-2 py-0.5 text-xs text-text-3 capitalize shrink-0">
                    {p.coffee_style}
                  </span>
                )}
              </div>

              <div className="flex gap-3 text-sm">
                {p.acidity_pref != null && (
                  <span className="text-text-3">Acidity <span className="text-text font-medium">{p.acidity_pref}</span></span>
                )}
                {p.body_pref != null && (
                  <span className="text-text-3">Body <span className="text-text font-medium">{p.body_pref}</span></span>
                )}
                {p.sweetness_pref != null && (
                  <span className="text-text-3">Sweet <span className="text-text font-medium">{p.sweetness_pref}</span></span>
                )}
              </div>

              {p.notes && (
                <p className="text-xs text-text-3 line-clamp-2">{p.notes}</p>
              )}

              <div className="flex items-center gap-3 mt-auto pt-2 border-t border-border">
                <a
                  href={`/dashboard/owner/blends/new?preset_id=${p.id}`}
                  className="text-xs text-brand-600 hover:underline"
                >
                  Use in new blend
                </a>
                <button
                  onClick={() => handleDelete(p.id, p.name)}
                  disabled={isPending}
                  className="ml-auto text-xs text-text-3 hover:text-danger disabled:opacity-40"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
