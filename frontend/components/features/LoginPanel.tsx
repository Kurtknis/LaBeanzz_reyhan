"use client";

import { useEffect, useState } from "react";
import { signIn, signOut } from "next-auth/react";
import {
  GOOGLE_FAILURE_CODES,
  GUEST_ERROR_CODES,
  LOGIN_COPY,
  LOGIN_MESSAGES,
  SESSION_EXPIRED_CODE,
} from "@/product.config";

interface LoginPanelProps {
  /** Decided on the server at request time, never baked into the client bundle */
  guestEnabled: boolean;
  /** Auth.js error code from the redirect back to /login, if any */
  errorCode: string | null;
  callbackUrl: string;
}

type Pending = "google" | "guest" | null;

function messageFor(errorCode: string | null, guestEnabled: boolean): string | null {
  if (!errorCode) return null;
  if (errorCode === SESSION_EXPIRED_CODE) return LOGIN_MESSAGES.sessionExpired;
  if ((GOOGLE_FAILURE_CODES as readonly string[]).includes(errorCode)) {
    return guestEnabled ? LOGIN_MESSAGES.googleDownWithGuest : LOGIN_MESSAGES.googleDown;
  }
  if (errorCode === "AccessDenied") return LOGIN_MESSAGES.accessDenied;
  return LOGIN_MESSAGES.generic;
}

export function LoginPanel({ guestEnabled, errorCode, callbackUrl }: LoginPanelProps) {
  const [pending, setPending] = useState<Pending>(null);
  const [guestError, setGuestError] = useState<string | null>(null);

  const googleFailed = (GOOGLE_FAILURE_CODES as readonly string[]).includes(errorCode ?? "");
  const message = guestError ?? messageFor(errorCode, guestEnabled);
  // Point at the way forward when Google is the thing that is broken
  const highlightGuest = guestEnabled && googleFailed;

  // Arriving here because a session ran out: drop the stale cookie so it can't confuse later requests
  useEffect(() => {
    if (errorCode === SESSION_EXPIRED_CODE) void signOut({ redirect: false });
  }, [errorCode]);

  async function continueAsGuest() {
    setPending("guest");
    setGuestError(null);
    try {
      const result = await signIn("guest", { redirect: false });
      if (result?.error) {
        const key = GUEST_ERROR_CODES[(result.code ?? "") as keyof typeof GUEST_ERROR_CODES] ?? "guestUnavailable";
        setGuestError(LOGIN_MESSAGES[key]);
        setPending(null);
        return;
      }
      // A full navigation, so the server renders with the new session cookie
      window.location.assign(callbackUrl);
    } catch {
      setGuestError(LOGIN_MESSAGES.guestUnavailable);
      setPending(null);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-2 px-4 py-8">
      <div className="w-full max-w-sm rounded-xl border border-border bg-surface p-6 shadow-sm sm:p-8">
        <div className="mb-8 text-center">
          <span className="text-2xl font-semibold tracking-tight text-brand-700">LaBeans</span>
          <p className="mt-1 text-sm text-text-3">{LOGIN_COPY.tagline}</p>
        </div>

        <h1 className="mb-6 text-center text-lg font-medium text-text">{LOGIN_COPY.title}</h1>

        {message && (
          <p
            role="alert"
            className="mb-4 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2.5 text-sm text-text-2"
          >
            {message}
          </p>
        )}

        <button
          type="button"
          disabled={pending !== null}
          onClick={() => {
            setPending("google");
            void signIn("google", { callbackUrl });
          }}
          className="flex min-h-11 w-full items-center justify-center gap-3 rounded-lg border border-border bg-surface px-4 py-2.5 text-sm font-medium text-text transition-colors hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <GoogleIcon />
          {LOGIN_COPY.google}
        </button>

        {guestEnabled && (
          <>
            <div className="my-4 flex items-center gap-3" aria-hidden="true">
              <span className="h-px flex-1 bg-border" />
              <span className="text-xs text-text-3">{LOGIN_COPY.divider}</span>
              <span className="h-px flex-1 bg-border" />
            </div>

            <button
              type="button"
              disabled={pending !== null}
              onClick={continueAsGuest}
              className={`flex min-h-11 w-full items-center justify-center rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:cursor-not-allowed disabled:opacity-60 ${
                highlightGuest
                  ? "border-brand-500 bg-brand-50 text-brand-800 ring-2 ring-brand-500 hover:bg-brand-100"
                  : "border-border bg-surface-2 text-text-2 hover:bg-surface-3"
              }`}
            >
              {pending === "guest" ? LOGIN_COPY.guestPending : LOGIN_COPY.guest}
            </button>
            <p className="mt-2 text-center text-xs text-text-3">{LOGIN_COPY.guestHint}</p>
          </>
        )}

        <p className="mt-6 text-center text-xs text-text-3">{LOGIN_COPY.terms}</p>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"
        fill="#4285F4"
      />
      <path
        d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"
        fill="#34A853"
      />
      <path
        d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z"
        fill="#FBBC05"
      />
      <path
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z"
        fill="#EA4335"
      />
    </svg>
  );
}
