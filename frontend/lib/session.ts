import type { Session } from "next-auth";

/**
 * Extended session shape carrying our app-specific fields.
 * We store these in the JWT callback and read them back in the session callback.
 *
 * For guest sessions appToken is never set: the app JWT stays inside the
 * encrypted session cookie and is attached to API calls by /api/proxy on the server.
 */
export interface AppSession extends Session {
  appToken?: string;
  /** Guest sessions only: when the guest's API token stops working (ISO 8601) */
  guestExpiresAt?: string;
  /** Guest sessions only: how long the server keeps guest data */
  guestPurgeHours?: number;
  user: Session["user"] & {
    id?: string;
    role?: string | null;
    isGuest?: boolean;
  };
}
