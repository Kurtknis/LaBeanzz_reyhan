"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import Link from "next/link";
import {
  analyzeFeedback,
  sendChat,
  type ChatMessage,
  type FeedbackAnalysis,
} from "@/lib/api/ai";
import { errorMessage } from "@/lib/api/orders";

type Tab = "chat" | "feedback";

const STARTERS = [
  "What makes a good milk-drink espresso blend?",
  "Which of the current beans work best for a fruity filter coffee?",
  "How does roast level change acidity?",
];

const ADJUSTMENT_LABELS: Record<string, string> = {
  acidity_max: "Maximum acidity",
  body_min: "Minimum body",
  sweetness_min: "Minimum sweetness",
};

function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isPending]);

  function send(text: string) {
    const content = text.trim();
    if (!content || isPending) return;
    const next: ChatMessage[] = [...messages, { role: "user", content }];
    setMessages(next);
    setDraft("");
    setError(null);

    startTransition(async () => {
      try {
        // The server accepts at most 20 messages, so send the most recent ones
        const { reply } = await sendChat(next.slice(-20));
        setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
      } catch (err) {
        setError(errorMessage(err, "The assistant could not answer. Please try again."));
      }
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-text-3">
        Ask anything about coffee. Answers use the live bean catalog and your own feedback
        constraints. Nothing here is saved to your blends; the conversation is gone when you leave.
      </p>

      <div className="flex min-h-72 flex-col gap-3 rounded-xl border border-border bg-surface p-4">
        {messages.length === 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-text-3">Try one of these:</p>
            {STARTERS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="self-start rounded-full border border-border px-3 py-1 text-left text-sm text-text-2 hover:border-brand-400 hover:text-brand-700"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] whitespace-pre-wrap rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
              m.role === "user" ? "self-end bg-brand-500 text-white" : "self-start bg-surface-2 text-text"
            }`}
          >
            {m.content}
          </div>
        ))}

        {isPending && <div className="self-start rounded-xl bg-surface-2 px-4 py-2.5 text-sm text-text-3">Thinking…</div>}
        <div ref={bottom} />
      </div>

      {error && <p role="alert" className="text-sm text-danger">{error}</p>}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
        className="flex gap-2"
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          maxLength={2000}
          placeholder="Ask a question…"
          aria-label="Your message"
          className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-3 focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <button
          type="submit"
          disabled={!draft.trim() || isPending}
          className="rounded-lg bg-brand-500 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
        >
          Send
        </button>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={() => {
              setMessages([]);
              setError(null);
            }}
            className="rounded-lg border border-border px-3 py-2 text-sm text-text-3 hover:text-text"
          >
            Clear
          </button>
        )}
      </form>
    </div>
  );
}

function FeedbackAnalysisView() {
  const [result, setResult] = useState<FeedbackAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [needsFeedback, setNeedsFeedback] = useState(false);
  const [isPending, startTransition] = useTransition();

  function run() {
    setError(null);
    setNeedsFeedback(false);
    startTransition(async () => {
      try {
        setResult(await analyzeFeedback());
      } catch (err) {
        const status = (err as { status?: number }).status;
        if (status === 422) setNeedsFeedback(true);
        else setError(errorMessage(err, "The analysis could not be completed."));
      }
    });
  }

  const adjustments = result ? Object.entries(result.taste_adjustments) : [];

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-text-3">
        Summarises the feedback you have left on your blends and refreshes the constraints used for
        your next generation. The constraints come from simple rating thresholds, not from a trained model.
      </p>

      <button
        onClick={run}
        disabled={isPending}
        className="self-start rounded-lg bg-brand-500 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
      >
        {isPending ? "Analysing…" : result ? "Run again" : "Analyse my feedback"}
      </button>

      {needsFeedback && (
        <div className="rounded-xl border border-border bg-surface p-5 text-sm text-text-2">
          You have not left any feedback yet. Open one of your{" "}
          <Link href="/dashboard/owner/blends" className="text-brand-600 hover:underline">blends</Link>{" "}
          and rate it, then come back.
        </div>
      )}
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}

      {result && (
        <div className="flex flex-col gap-4">
          <div className="rounded-xl border border-border bg-surface p-5">
            <h2 className="text-sm font-semibold text-text">Summary</h2>
            <p className="mt-2 text-sm leading-relaxed text-text-2">{result.summary}</p>
            {result.patterns.length > 0 && (
              <ul className="mt-3 flex list-disc flex-col gap-1 pl-5 text-sm text-text-2">
                {result.patterns.map((p) => <li key={p}>{p}</li>)}
              </ul>
            )}
          </div>

          <div className="rounded-xl border border-border bg-surface p-5">
            <h2 className="text-sm font-semibold text-text">Ratings by brew style</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-text-3">
                    <th className="pb-2 font-medium">Style</th>
                    <th className="pb-2 text-right font-medium">Entries</th>
                    <th className="pb-2 text-right font-medium">Overall</th>
                    <th className="pb-2 text-right font-medium">Acidity</th>
                    <th className="pb-2 text-right font-medium">Body</th>
                    <th className="pb-2 text-right font-medium">Sweetness</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.stats).map(([ctx, s]) => (
                    <tr key={ctx} className="border-b border-border/50 last:border-0">
                      <td className="py-2 capitalize">{ctx}</td>
                      <td className="py-2 text-right tabular-nums">{s.count}</td>
                      <td className="py-2 text-right tabular-nums">{s.overall}</td>
                      <td className="py-2 text-right tabular-nums">{s.acidity}</td>
                      <td className="py-2 text-right tabular-nums">{s.body}</td>
                      <td className="py-2 text-right tabular-nums">{s.sweetness}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-surface p-5">
            <h2 className="text-sm font-semibold text-text">Adjusted using your previous feedback</h2>
            {adjustments.length === 0 ? (
              <p className="mt-2 text-sm text-text-3">No constraints are active. Your ratings are balanced.</p>
            ) : (
              <ul className="mt-3 flex flex-col gap-1.5">
                {adjustments.flatMap(([ctx, rules]) =>
                  Object.entries(rules).map(([key, value]) => (
                    <li key={`${ctx}-${key}`} className="rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-800">
                      <span className="capitalize">{ctx}</span>: {ADJUSTMENT_LABELS[key] ?? key} {value}
                    </li>
                  ))
                )}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function AILabPage() {
  const [tab, setTab] = useState<Tab>("chat");

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text">AI Lab</h1>
        <p className="mt-1 text-sm text-text-3">
          A free-form space to experiment. For a guided recipe, use{" "}
          <Link href="/dashboard/owner/blends/new" className="text-brand-600 hover:underline">New blend</Link>.
        </p>
      </div>

      <div className="flex gap-2">
        {([["chat", "Chat"], ["feedback", "Feedback analysis"]] as const).map(([value, label]) => (
          <button
            key={value}
            onClick={() => setTab(value)}
            className={`rounded-full px-3 py-1 text-sm transition-colors ${
              tab === value ? "bg-brand-500 text-white" : "border border-border text-text-2 hover:bg-surface-2"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "chat" ? <Chat /> : <FeedbackAnalysisView />}
    </div>
  );
}
