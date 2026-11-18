import { getToken } from "next-auth/jwt";
import type { NextRequest } from "next/server";

const SECURE_COOKIE_PREFIX = "__Secure-authjs.session-token";

export interface ServerSessionToken {
  appToken?: string;
  isGuest?: boolean;
}

/**
 * Reads the decrypted session cookie on the server. Used where the app token is
 * needed but must not be part of the session object the browser can fetch
 * (guest sessions). Never call this from client code.
 */
export async function readSessionToken(req: NextRequest): Promise<ServerSessionToken | null> {
  const cookie = req.headers.get("cookie") ?? "";
  // Over HTTPS Auth.js uses the __Secure- prefixed cookie name (and may split it into chunks)
  const secureCookie = cookie.includes(SECURE_COOKIE_PREFIX);

  // Only the cookie is passed on, so an Authorization header can't stand in for a session
  const token = await getToken({
    req: { headers: new Headers({ cookie }) },
    secret: process.env.AUTH_SECRET,
    secureCookie,
  });
  return token as ServerSessionToken | null;
}
