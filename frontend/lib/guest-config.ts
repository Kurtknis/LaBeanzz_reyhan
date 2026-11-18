/**
 * Server-side only. Read at request time (never inlined at build time), so the
 * flag can change by editing an environment variable and restarting.
 *
 * An explicit GUEST_LOGIN_ENABLED wins. Otherwise: on for local development and
 * Vercel preview deployments, off for production.
 */
export function guestLoginEnabled(): boolean {
  const explicit = process.env.GUEST_LOGIN_ENABLED?.trim().toLowerCase();
  if (explicit) return ["1", "true", "yes", "on"].includes(explicit);

  const vercelEnv = process.env.VERCEL_ENV;
  if (vercelEnv) return vercelEnv !== "production";
  return process.env.NODE_ENV !== "production";
}
