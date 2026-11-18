/**
 * Base fetch wrapper. Every call goes through the Next proxy (/api/proxy/*),
 * which attaches the app JWT from the session cookie.
 *
 * In the browser the cookie travels automatically. A server component has no
 * browser, so there the incoming request's cookies are forwarded explicitly;
 * without them the proxy sees no session and redirects to /login.
 */

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown
  ) {
    super(`API error ${status}`);
  }
}

type Method = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

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

  if (res.type === "opaqueredirect" || (res.status >= 300 && res.status < 400)) {
    throw new ApiError(401, { error: "Not signed in." });
  }

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorBody);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}
