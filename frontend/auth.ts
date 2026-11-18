import NextAuth, { CredentialsSignin } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";
import type { AppSession } from "@/lib/session";
import { guestLoginEnabled } from "@/lib/guest-config";

// Errors surfaced to the login page by signIn("guest"). The `code` reaches the
// browser as `result.code`; see GUEST_ERROR_CODES in product.config.ts.
class GuestLoginDisabled extends CredentialsSignin {
  code = "guest_disabled";
}
class GuestLoginLimited extends CredentialsSignin {
  code = "guest_limited";
}
class GuestLoginUnavailable extends CredentialsSignin {
  code = "guest_unavailable";
}

interface GuestUser {
  id: string;
  name: string;
  email: string;
  appToken: string;
  role: string | null;
  isGuest: true;
  guestExpiresAt: string;
  guestPurgeHours: number;
}

/** The visitor's address as seen by the platform in front of Next.js. */
function visitorIp(request: Request): string | undefined {
  const forwarded = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  return forwarded || request.headers.get("x-real-ip") || undefined;
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
    }),
    // Fallback for when Google sign-in is unavailable. Runs on the server only:
    // it asks Flask for a guest account and the token goes straight into the
    // encrypted session cookie, the same place the Google flow puts it.
    Credentials({
      id: "guest",
      name: "Guest",
      credentials: {},
      async authorize(_credentials, request): Promise<GuestUser | null> {
        if (!guestLoginEnabled()) throw new GuestLoginDisabled();

        const headers: Record<string, string> = { "Content-Type": "application/json" };
        // Flask sees this server's address, not the visitor's. Forward the visitor's
        // so per-IP limits mean something; Flask trusts it only with the shared secret.
        const sharedSecret = process.env.GUEST_PROXY_SECRET;
        const ip = visitorIp(request);
        if (sharedSecret && ip) {
          headers["X-Client-IP"] = ip;
          headers["X-Internal-Secret"] = sharedSecret;
        }

        let res: Response;
        try {
          res = await fetch(`${process.env.BACKEND_URL}/api/auth/guest`, {
            method: "POST",
            headers,
            body: "{}",
            cache: "no-store",
          });
        } catch {
          throw new GuestLoginUnavailable();
        }

        if (res.status === 404) throw new GuestLoginDisabled();
        if (res.status === 429) throw new GuestLoginLimited();
        if (!res.ok) throw new GuestLoginUnavailable();

        const data = await res.json();
        return {
          id: data.user.id,
          name: data.user.name,
          email: data.user.email,
          appToken: data.token,
          role: data.user.role ?? null,
          isGuest: true,
          guestExpiresAt: data.guest.expires_at,
          guestPurgeHours: data.guest.purge_after_hours,
        };
      },
    }),
  ],
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, account, user, trigger }) {
      // On first sign-in exchange the Google ID token for our app JWT
      if (account?.id_token) {
        try {
          const res = await fetch(
            `${process.env.BACKEND_URL}/api/auth/google`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ credential: account.id_token }),
            }
          );
          if (res.ok) {
            const data = await res.json();
            token["appToken"] = data.token;
            token["role"] = data.user.role;
            token["userId"] = data.user.id;
          }
        } catch {
          // Backend unreachable during token exchange — handled at session level
        }
      }

      // Guest sign-in: authorize() already did the exchange
      if (account?.provider === "guest" && user) {
        const guest = user as unknown as GuestUser;
        token["appToken"] = guest.appToken;
        token["role"] = guest.role;
        token["userId"] = guest.id;
        token["isGuest"] = true;
        token["guestExpiresAt"] = guest.guestExpiresAt;
        token["guestPurgeHours"] = guest.guestPurgeHours;
      }

      // useSession().update() lands here. Whatever the browser sent is ignored:
      // the role is re-read from the API with the token we already hold, so a
      // client cannot grant itself a role, and no token has to travel to the browser.
      if (trigger === "update" && token["appToken"]) {
        try {
          const res = await fetch(`${process.env.BACKEND_URL}/api/auth/me`, {
            headers: { Authorization: `Bearer ${token["appToken"]}` },
            cache: "no-store",
          });
          if (res.ok) {
            const me = await res.json();
            token["role"] = me.role;
            token["isGuest"] = Boolean(me.is_guest);
          }
        } catch {
          // Keep the current session; the next update will retry
        }
      }
      return token;
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async session({ session, token }): Promise<any> {
      const s = session as AppSession;
      const isGuest = token["isGuest"] === true;
      // A guest's app token never leaves the server (the proxy reads it from the cookie)
      if (!isGuest) s.appToken = token["appToken"] as string | undefined;
      s.user = {
        ...s.user,
        role: token["role"] as string | null | undefined,
        id: token["userId"] as string | undefined,
        isGuest,
      };
      if (isGuest) {
        s.guestExpiresAt = token["guestExpiresAt"] as string | undefined;
        s.guestPurgeHours = token["guestPurgeHours"] as number | undefined;
      }
      return s;
    },
  },
  pages: {
    signIn: "/login",
    // Send OAuth failures to our own page so it can offer the guest fallback
    error: "/login",
  },
});
