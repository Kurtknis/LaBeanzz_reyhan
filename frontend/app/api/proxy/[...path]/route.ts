import { auth } from "@/auth";
import type { AppSession } from "@/lib/session";
import { readSessionToken } from "@/lib/server-session";
import { NextRequest, NextResponse } from "next/server";

// Allow AI generation calls time to complete
export const maxDuration = 60;

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:5000";

// Sign-in exchanges happen on the server inside Auth.js. They are not for browsers:
// reaching them through here would hand a raw app token to client-side JS.
const SERVER_ONLY_PATHS = new Set(["auth/guest", "auth/google"]);

function notFound() {
  return NextResponse.json({ error: "Not found." }, { status: 404 });
}

async function proxyRequest(req: NextRequest, params: { path: string[] }) {
  // Refuse anything that could be used to dodge the checks below
  if (params.path.some((s) => s === "" || s === "." || s === ".." || /[\\/%]/.test(s))) {
    return notFound();
  }
  const upstreamPath = params.path.join("/");
  if (SERVER_ONLY_PATHS.has(upstreamPath.toLowerCase())) return notFound();

  const session = (await auth()) as AppSession | null;
  // Guest sessions deliberately leave appToken out of the session the browser can read,
  // so fall back to the encrypted cookie itself.
  const cookieToken = session?.appToken ? null : await readSessionToken(req);
  const appToken = session?.appToken ?? cookieToken?.appToken;
  const isGuest = Boolean(session?.user?.isGuest ?? cookieToken?.isGuest);

  const search = req.nextUrl.search;
  const url = `${BACKEND}/api/${upstreamPath}${search}`;

  const headers = new Headers();
  headers.set("Content-Type", req.headers.get("Content-Type") ?? "application/json");
  if (appToken) {
    headers.set("Authorization", `Bearer ${appToken}`);
  }

  const body =
    req.method !== "GET" && req.method !== "HEAD"
      ? await req.arrayBuffer()
      : undefined;

  const upstream = await fetch(url, {
    method: req.method,
    headers,
    body: body ? Buffer.from(body) : undefined,
  });

  let responseBody: ArrayBuffer | string = await upstream.arrayBuffer();
  const contentType = upstream.headers.get("Content-Type") ?? "application/json";

  // Onboarding returns a fresh token. A guest's must not reach browser JS; the
  // session cookie already holds a valid one and the role is refreshed server-side.
  if (isGuest && upstreamPath.startsWith("auth/") && contentType.includes("application/json")) {
    try {
      const parsed = JSON.parse(new TextDecoder().decode(responseBody));
      if (parsed && typeof parsed === "object" && "token" in parsed) {
        delete parsed.token;
        responseBody = JSON.stringify(parsed);
      }
    } catch {
      // Not JSON after all: pass it through untouched
    }
  }

  return new NextResponse(responseBody, {
    status: upstream.status,
    headers: { "Content-Type": contentType },
  });
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(req, await params);
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(req, await params);
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(req, await params);
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(req, await params);
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(req, await params);
}
