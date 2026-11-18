"use client";

import { useState, useSyncExternalStore } from "react";
import { signOut } from "next-auth/react";
import { GUEST_BANNER } from "@/product.config";

const DISMISSED_KEY = "labeans.guest-banner.dismissed";
const listeners = new Set<() => void>();

function subscribe(onChange: () => void) {
  listeners.add(onChange);
  return () => {
    listeners.delete(onChange);
  };
}

function isDismissed(): boolean {
  try {
    return window.sessionStorage.getItem(DISMISSED_KEY) === "1";
  } catch {
    return false; // storage blocked: show the banner rather than hide a warning
  }
}

/**
 * Shown on every page of a guest session. Dismissing hides it for this browser tab
 * session only, so a returning guest is reminded again.
 */
export function GuestBanner({ purgeHours }: { purgeHours?: number }) {
  const dismissed = useSyncExternalStore(subscribe, isDismissed, () => true);
  const [confirming, setConfirming] = useState(false);

  if (dismissed) return null;

  function dismiss() {
    try {
      window.sessionStorage.setItem(DISMISSED_KEY, "1");
    } catch {
      // ignore: it will simply reappear on the next page
    }
    listeners.forEach((notify) => notify());
  }

  return (
    <div
      role="status"
      className="flex flex-col gap-2 border-b border-warning/30 bg-warning/10 px-4 py-2.5 text-sm text-text-2 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex flex-col gap-1">
        <p>
          {GUEST_BANNER.message(purgeHours)}{" "}
          {!confirming && (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              className="font-medium text-brand-700 underline underline-offset-2 hover:text-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              {GUEST_BANNER.signInWithGoogle}
            </button>
          )}
        </p>
        {confirming && (
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <p className="text-text">{GUEST_BANNER.confirmText}</p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void signOut({ callbackUrl: "/login" })}
                className="rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                {GUEST_BANNER.confirm}
              </button>
              <button
                type="button"
                onClick={() => setConfirming(false)}
                className="rounded-lg border border-border px-3 py-1.5 text-xs text-text-2 hover:bg-surface"
              >
                {GUEST_BANNER.cancel}
              </button>
            </div>
          </div>
        )}
      </div>
      <button
        type="button"
        onClick={dismiss}
        aria-label={GUEST_BANNER.dismiss}
        className="self-end rounded p-1 text-text-3 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 sm:self-auto"
      >
        ✕
      </button>
    </div>
  );
}
