/**
 * Base fetch wrapper. Every call goes through the Next proxy (/api/proxy/*),
 * which attaches the app JWT from the session cookie.
 *
 * In the browser the cookie travels automatically. A server component has no
 * browser, so there the incoming request's cookies are forwarded explicitly;
 * without them the proxy sees no session and redirects to /login.
 */

import { redirect } from "next/navigation";
import { SESSION_EXPIRED_CODE } from "@/product.config";

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown
  ) {
    super(`API error ${status}`);
  }
}

type Method = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

/**
 * The session is no longer valid (a guest's 4-hour token ran out, the account was
 * purged, a Google session timed out). Clear the stale cookie and send the user to
 * the login page with an explanation instead of leaving a half-working page.
 */
async function endSession(): Promise<never> {
  const loginUrl = `/login?error=${SESSION_EXPIRED_CODE}`;
  if (typeof window === "undefined") redirect(loginUrl);

  const { signOut } = await import("next-auth/react");
  await signOut({ redirect: false }).catch(() => undefined);
  // A hard navigation on purpose: it throws away all client state tied to the dead session
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign(loginUrl);
  // Never settle: callers must not flash an error state while the browser navigates away
  return new Promise<never>(() => undefined);
}

interface ServerContext {
  base: string;
  cookie?: string;
}

/** Where to reach this app from the server, and whose cookies to send. */
async function serverContext(): Promise<ServerContext> {
  // Loaded lazily so client components that import this module never pull it in
  const { headers } = await import("next/headers");
  const incoming = await headers();

  const configured = process.env.AUTH_URL ?? process.env.NEXTAUTH_URL;
  if (configured) {
    return { base: configured.replace(/\/$/, ""), cookie: incoming.get("cookie") ?? undefined };
  }

  const host = incoming.get("x-forwarded-host") ?? incoming.get("host") ?? "localhost:3000";
  const proto = incoming.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  return { base: `${proto}://${host}`, cookie: incoming.get("cookie") ?? undefined };
}

export async function apiFetch<T>(
  path: string,
  options: {
    method?: Method;
    body?: unknown;
    next?: NextFetchRequestConfig;
  } = {}
): Promise<T> {
  const { method = "GET", body, next } = options;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  let base = "";

  if (typeof window === "undefined") {
    const ctx = await serverContext();
    base = ctx.base;
    if (ctx.cookie) headers["Cookie"] = ctx.cookie;
  }

  const res = await fetch(`${base}/api/proxy/${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    next,
    // The response depends on who is asking
    cache: "no-store",
    // A redirect here means "no session"; surface it as an error, not as HTML
    redirect: "manual",
  });

  // A redirect means the proxy found no session; a 401 means the API rejected the token
  if (res.type === "opaqueredirect" || (res.status >= 300 && res.status < 400) || res.status === 401) {
    return endSession();
  }

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}
