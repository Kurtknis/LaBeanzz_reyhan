I'll start by reading the Phase 6/7 doc and the files this feature touches, then post the file list and any blueprint conflicts before writing code.Posting the plan and conflicts now. None of them need your answer before I start, but you should see them.

## Plan

**Backend (create):** `migrations/versions/0007_guest_users.py`, `services/guest_service.py` (create, daily cap, purge, client IP), `services/visibility.py`, `scripts/purge_guests.py`, `tests/test_guest.py`.
**Backend (modify):** `models/user.py`, `config.py`, `services/jwt_service.py`, `decorators.py` (stash claims, no logic change), `routes/auth.py`, `routes/ai.py`, `routes/coffee_beans.py`, `routes/suppliers.py`, plus the places that read beans for an owner (`blend_generation_service`, `blend_service`, `order_service`, `ai_lab_service`, `insights_service`, `stock_service`), `.env.example`, `tests/conftest.py`.
**Frontend (create):** `components/features/LoginPanel.tsx`, `GuestBanner.tsx`, `frontend/.env.example`.
**Frontend (modify):** `auth.ts`, `lib/session.ts`, `lib/api/client.ts`, `app/login/page.tsx`, `app/api/proxy/[...path]/route.ts`, `app/onboarding/page.tsx`, both dashboard layouts, `product.config.ts`, `.gitignore`.

## Conflicts and decisions
1. **Token exposure.** The Google flow's session callback hands `appToken` to browser JS, and onboarding returns a token to the browser. Your requirement forbids that for guests, and the blueprint (§0.2) says the same. For guests I'll keep the token out of the session and have the proxy read it from the encrypted cookie. The proxy will also strip `token` from guest `/auth/*` responses and refuse `/api/proxy/auth/guest` and `/api/proxy/auth/google`. Otherwise the browser could mint a guest token itself. I'm leaving the Google path as it is, and I'll flag the gap in the summary.
2. **Onboarding session refresh.** The existing `jwt` callback ignores `update()`, so a new role may never reach the cookie. I'll test that. If it is broken, I'll add a server-side refresh from `/auth/me`. That helps both flows and trusts nothing from the client.
3. **Client IP.** Flask sees Vercel's egress IP, not the user's. I'll forward the real IP from `authorize()`, trusted only with a shared secret header. The daily cap needs durable storage, so I'm adding a `users.guest_ip_hash` column (HMAC of the IP, never the raw IP).
4. **Guest isolation.** Guest owners see and order only seeded demo suppliers (`GUEST_ORDER_DEMO_SUPPLIERS_ONLY`, default on). Guest suppliers' beans and profiles are visible only to themselves. Otherwise guest-written text would flow into real owners' LLM prompts and catalogs. The cost is that a guest supplier gets no orders.
5. **Smaller deviations.** Errors stay as `{"error": "<string>"}`, because the whole codebase and frontend use that and not the blueprint's object. There is no `app/auth/` package, so I'm using the existing `services/` layout. Zod isn't installed and the browser sends no new request bodies, so no Zod mirrors. The frontend has no test runner, so I'll verify the UI in a real browser instead.

First I'll check whether onboarding refresh is actually broken today.The environment survived. I'll check the onboarding question on the current code: a freshly signed-in Google-style user with no role goes through onboarding in the browser.That shell command failed to parse, so the servers started but the user and cookie weren't created. I'll put the script in a file instead.The script lives in `/tmp`, so Python doesn't have the backend on its path. I'll set `PYTHONPATH`.Now config. The feature flag defaults differ by environment: on for development, off for production.Now the visibility rule: one helper that says which suppliers a user may see or order from, applied at every place an owner reads beans.Now the service-level places that read beans for an owner.`blend_service` also needs its import, then the order creation check. Hidden beans are treated exactly like nonexistent ones, so a stranger's bean id returns the same 404 as a random id.Now the auth routes: the new `/auth/guest`, and onboarding so that a fresh token can't extend a guest's session.Now the lower AI limit for guests. The limit value is chosen per request from the authenticated user's database record, not from a claim in the token.All 42 pass on the first run, which is exactly when I should check that they can fail. I'll mutate the five security-critical behaviours one at a time and confirm a test catches each.The write and the run happened in parallel, so the file wasn't there yet. Rerunning.Now `auth.ts`. The Google branch is byte-for-byte unchanged. I'm adding the guest provider, a server-side `update()` refresh, and the guest fields on the session.Now the proxy route. It reads the guest token from the cookie server-side, refuses to forward the two sign-in endpoints, and strips any `token` from guest `/auth/*` responses.Now onboarding. The page stops reading and forwarding a token, and just calls `update()`, which refreshes the role server-side. That fixes the stuck-on-onboarding bug for both flows.Now the dashboard layouts: the banner, and a clean redirect when a guest's token has expired. Then `unstable_rethrow` in the server pages that swallow errors.Now the frontend `.env.example` (git currently ignores every `.env*` file, so I'm adding an exception), then typecheck and lint.The build passes, and `/login` is now rendered per request (`ƒ`), which is what makes the flag a runtime setting. I'll start both servers with the guest flag on and a shared proxy secret.Both servers are up. I'll run the guest flow in a real browser end to end: sign-in, onboarding, token exposure checks, the banner, the Google-failure fallback, session expiry and the rate limit.Same race as before: the file write and the run were issued together. Running it again.Still stuck, so I'll look at the network again.The same write-then-run race again. I'll run it now that the file exists.The flag works at runtime: same build, a restart with the env var changed, and the button, message and provider all follow it. I'll look at the screenshots."Continue as Guest" is in and working, and none of the access rules got weaker. A guest is a normal user row with `is_guest = true`. It goes through the same `/auth/onboard`, decorators and owner-scoped queries as everyone else, with no special cases in `@require_auth` or `@require_role`. Nothing is committed or deployed.

## What I ran
- **Backend tests:** 189 pass on real Postgres with pgvector. That includes 42 new guest tests, and the existing Google and IDOR tests pass unchanged.
- **Checking the tests catch real bugs:** I broke 9 key behaviours one at a time, such as the purge forgetting to release stock or guests getting the normal AI limit. A test failed for each one. Two tests missed their bug on the first try, and I strengthened them.
- **Migration:** `0007` upgrades with existing users kept, downgrades cleanly, and has no model drift.
- **Browser:** 38 checks in headless Chromium against a production build, plus 5 more with the flag off. They cover login, the Google-failure fallback, onboarding, the banner, mobile layout, expiry, rate limits, and searching every response for a token. The token search found a JWT in a Google session, so it would catch a leak.
- **Not tested:** real Google OAuth (I triggered Auth.js errors locally instead) and anything on Vercel or Railway.

## Decisions you should know about
- **Guest isolation.** Guest owners only see and order from seeded demo suppliers, set by `GUEST_ORDER_DEMO_SUPPLIERS_ONLY` (default on). Guest suppliers' beans and profiles are visible only to that guest. The reason is that bean text feeds other owners' AI prompts, and a test confirms an injected bean name never reaches a real owner's prompt. The cost is that a guest supplier never receives orders. Hidden beans return the same 404 as missing ones, so guests can't tell them apart.
- **Guest tokens stay on the server.** The guest session object has no `appToken`. The proxy reads the token from the encrypted cookie, removes `token` from guest `/auth/*` responses, and returns 404 for `auth/guest` and `auth/google`.
- **Google sessions still expose `appToken` to browser JS.** You asked me not to change the Google flow, so I didn't. It goes against blueprint §0.2, and it's worth fixing next.
- **Visitor IP.** Flask only sees the Vercel server's address. `authorize()` forwards the visitor's IP, and Flask trusts it only when `GUEST_PROXY_SECRET` matches. The daily cap stores an HMAC of the IP, never the raw address.
- **Error format.** Errors stay as `{"error": "..."}` to match the current code and frontend, not the blueprint's object format.
- **No Zod schemas.** Zod isn't installed and no new browser request bodies needed validating.
- **No frontend test runner.** I covered the frontend with browser scripts in `/tmp` instead; they are not in the repo.

## Fixes to existing code
- **Onboarding left users stuck on `/onboarding`.** This was broken for Google users too. The middleware bounced the onboarding API call, and `update()` was ignored. The role is now re-read from `/auth/me` on the server, and nothing the browser sends is trusted.
- **Expired sessions.** A 401 now redirects to `/login?error=SessionExpired` and clears the cookie, in both client and server pages. I added `unstable_rethrow` to five server pages whose try/catch would have hidden that redirect.

## Env vars
| Var | Where | Default |
|---|---|---|
| `GUEST_LOGIN_ENABLED` | both | on in dev and Vercel preview, off in production. Read at request time, so a restart is enough. |
| `GUEST_PROXY_SECRET` | both, must match | none |
| `GUEST_JWT_TTL_HOURS` | backend | 4 |
| `GUEST_PURGE_AFTER_HOURS` | backend | 24 |
| `GUEST_RATE_LIMIT` | backend | `5 per minute` per IP |
| `GUEST_MAX_PER_IP_PER_DAY` | backend | 10 |
| `GUEST_AI_LIMIT` | backend | `3 per minute;30 per day` (regular users get 10/min) |
| `GUEST_ORDER_DEMO_SUPPLIERS_ONLY` | backend | true |
| `DEMO_SUPPLIER_SUB_PREFIX` | backend | `seed_` |

I added `frontend/.env.example` and un-ignored it in `.gitignore`.

## Migration and cleanup
```bash
cd backend && flask db upgrade                     # applies 0007
python -m scripts.purge_guests --dry-run           # shows what it would delete
python -m scripts.purge_guests                     # schedule this hourly
```
- **What it deletes:** only rows where `is_guest = true`. Real users and global `knowledge_chunks` are never matched. A test checks this with real accounts as old as the guests.
- **Safe to schedule:** a Postgres lock makes overlapping runs skip, and each guest is deleted in its own transaction.
- **Stock:** guests' open orders have their reserved stock released before deletion.
- **Failures:** the script exits 1 if any guest couldn't be purged, so a scheduler can alert on it.

The FK cascades already covered every dependent table. A test lists every foreign key that doesn't cascade, so a new one forces a review.

## Manual test
1. Start both apps with `GUEST_LOGIN_ENABLED=true` and the same `GUEST_PROXY_SECRET`, then run `scripts.seed`.
2. Open `/login`, click **Continue as Guest**, and pick Owner. You should land on the dashboard with the guest banner, and only demo beans in the catalog.
3. Open `/login?error=OAuthCallback` to see the fallback message and the highlighted guest button.
4. Delete your guest row in the database and reload. You should be sent to `/login` with "Your session has expired."

## Still open
- **Rate limits** use per-process memory. Multiple gunicorn workers each count separately. The daily cap is in the database, so it holds either way.
- **The purge is a script.** Nothing runs it until you add the Railway or Render cron job.
- **Banner dismissal** lasts for the browser tab session, then the banner returns as a reminder.