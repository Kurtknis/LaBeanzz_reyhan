Let me read all the required documents first.Good. Now let me read the current codebase state thoroughly before writing any code.Good. Let me also read the Next.js docs hint from AGENTS.md before writing any frontend code:Good. Now I have a complete picture. Let me plan Phase 4 carefully:

**Phase 4: Blend Management**
- Backend: `Blend`, `BlendItem`, `Preset` models + migration `0004`
- Routes: blends CRUD, presets CRUD, status transitions, duplicate
- Frontend: Save page, My Blends list, Blend detail/edit, Presets CRUD

Let me start building:Now the Alembic migration:Now the Pydantic schemas for blends and presets:Now the blend service — holds all business logic so routes stay thin:Now the preset service:Now the blends routes:Make sure the services package exports the new services:Register the blends blueprint in the app factory:Now also update the AI route to accept `preset_id` in the generate request — the blueprint needs to load preset data before calling generation. Let me check the current AI route:Good — the AI schema already accepts `preset_id`. Now let me check the blend_generation_service to see how presets are currently handled:Good — I can see the generation service already has the full pipeline, but it doesn't use `preset_id`. Now I need to wire in preset loading. Let me update the generation service to load presets when `preset_id` is supplied:Now verify backend syntax:Now build the frontend. I need:
1. `lib/api/blends.ts` and `lib/api/presets.ts`
2. `/dashboard/owner/blends/save` — save from AI draft
3. `/dashboard/owner/blends/page.tsx` — list (replace stub)
4. `/dashboard/owner/blends/[id]/page.tsx` — detail view
5. `/dashboard/owner/blends/[id]/edit/page.tsx` — edit recipe
6. `/dashboard/owner/presets/page.tsx` — presets list + create
7. `components/features/BlendRecipeEditor.tsx` — live-sum editor
8. Update the New Blend form to pass `preset_id`Now the `BlendRecipeEditor` component — the core of Phase 4 frontend:Now the Save page (from AI draft):Now replace the stub My Blends list page with the real one:Now create the blend detail and edit pages:Now build the presets page:Now update the New Blend page to read `preset_id` from the URL and send it to the API, and add it to the owner nav:Now update the New Blend page to read `preset_id` from the URL and pass it to the API:Now add the preset selector to the form in the New Blend page. Find where style selector ends:Now also update the owner dashboard quick links to include presets and fix the "New blend" CTA:Now run the build to check everything compiles:The error block in the form is missing a wrapper. Let me look at the exact content around that area:The original error block had a wrapping `{error && (` that got cut off. Fix it:`BlendStyle` isn't exported from `product.config.ts` — it has `BLEND_STATUS` but no `BlendStyle` type. Let me add it:Build passes clean with zero TypeScript errors — 24 routes now. Final backend syntax check:Phase 4 is done. Here's everything that was built:

---

**Backend**

| File | What it does |
|---|---|
| `app/models/blend.py` | `Blend` model — owner, name, description, status, style, version, `source_generation_id`, `predicted_profile`, `daily_usage_kg` |
| `app/models/blend_item.py` | `BlendItem` — blend→bean join with `percentage`; unique constraint on `(blend_id, coffee_bean_id)` |
| `app/models/preset.py` | `Preset` — per-owner named flavor targets; unique constraint on `(owner_id, name)` |
| `migrations/versions/0004_blends_and_presets.py` | Alembic migration `0003 → 0004` — all three tables with check constraints and indexes |
| `app/schemas/blends.py` | Pydantic: `CreateBlendRequest`, `PatchBlendRequest`, `BlendStatusRequest`, `CreatePresetRequest`, `PatchPresetRequest` — recipe sum validation and duplicate-bean detection in model validators |
| `app/services/blend_service.py` | Business logic: `create_blend`, `patch_blend` (bumps version on recipe edit), `set_blend_status` (enforces allowed transitions), `duplicate_blend`, `list_blends` |
| `app/services/preset_service.py` | `list_presets`, `create_preset`, `patch_preset`, `delete_preset` |
| `app/routes/blends.py` | Full REST surface: `GET/POST /blends`, `GET/PATCH /blends/:id`, `POST /blends/:id/status`, `POST /blends/:id/duplicate`, `GET/POST /presets`, `PATCH/DELETE /presets/:id` |
| `blend_generation_service.py` | Updated to load `Preset` by `preset_id` and merge its prefs into the generation prompt |

**Frontend (24 routes, zero TS errors)**

| Route | Purpose |
|---|---|
| `/dashboard/owner/blends` | My Blends list — status filter tabs, duplicate, archive inline |
| `/dashboard/owner/blends/new` | Existing AI form + preset selector (auto-fills style from preset) |
| `/dashboard/owner/blends/save` | Save from AI draft — recipe editor pre-populated from generation, editable before save |
| `/dashboard/owner/blends/[id]` | Detail view — recipe percentage bar, bean table, flavor profile bars, status actions |
| `/dashboard/owner/blends/[id]/edit` | Full edit — name, description, style, live-sum recipe editor; version bumps on save |
| `/dashboard/owner/presets` | Presets CRUD — create/delete, `Use in new blend` link passes `preset_id` |
| `components/features/BlendRecipeEditor.tsx` | Live-sum editor — per-row percentage inputs, add/remove beans, real-time total indicator (green/yellow/red) |
| `components/features/BlendActions.tsx` | Client component handling `DRAFT→ACTIVE` (requires daily usage kg), `→ARCHIVED`, `→ACTIVE`, duplicate |
| `lib/api/blends.ts` + `lib/api/presets.ts` | Typed API clients |
| `product.config.ts` | Added `BlendStyle` export |

**To deploy:** `flask db upgrade` applies migration `0004`. No seed changes needed — blends are user-created.