import type { AppSession } from "@/lib/session";

/** True once a guest's API token has run out. Regular sessions are handled by the 401 path in apiFetch. */
export function guestSessionExpired(session: AppSession | null): boolean {
  if (!session?.user?.isGuest || !session.guestExpiresAt) return false;
  return Date.now() >= Date.parse(session.guestExpiresAt);
}
