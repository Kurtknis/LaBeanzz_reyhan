import { connection } from "next/server";
import { LoginPanel } from "@/components/features/LoginPanel";
import { guestLoginEnabled } from "@/lib/guest-config";

// Rendered per request so the guest flag is read from the server's environment
// at runtime, not captured when the app was built.
export const instant = false;

/** Only same-site paths: never bounce a signed-in user to another origin. */
function safeCallback(value: string | undefined): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/";
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; callbackUrl?: string }>;
}) {
  await connection();
  const params = await searchParams;

  return (
    <LoginPanel
      guestEnabled={guestLoginEnabled()}
      errorCode={params.error ?? null}
      callbackUrl={safeCallback(params.callbackUrl)}
    />
  );
}
