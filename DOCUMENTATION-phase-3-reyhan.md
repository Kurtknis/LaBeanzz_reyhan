# DOCUMENTATION — Phase 3: AI Blend Generation
**Author:** Reyhan  
**Date:** 13 November 2026  
**Stack:** Flask 3.1 · PostgreSQL + pgvector · OpenRouter · Next.js 16 (App Router) · TypeScript

---

## Overview

Phase 3 adds the AI blend generator to LaBeans. An owner describes a coffee in plain language, and the system picks beans from the live catalog, retrieves relevant coffee knowledge, calls an LLM for a structured recipe, validates the output, and returns a draft with a computed flavor profile.

Nothing is saved as a blend until the owner explicitly clicks Save — generation and persistence are separate operations by design.

---

## What was built

### Backend

| File | Purpose |
|------|---------|
| `app/services/ai_service.py` | Single OpenRouter client: `complete_json()` and `embed()` |
| `app/services/rag_service.py` | Owner-scoped vector retrieval + chunk indexing |
| `app/services/blend_generation_service.py` | Full 8-step generation pipeline |
| `app/models/knowledge_chunk.py` | `knowledge_chunks` SQLAlchemy model |
| `app/models/ai_generation.py` | `ai_generations` SQLAlchemy model |
| `app/schemas/ai.py` | Pydantic request/response models with validation |
| `app/routes/ai.py` | `POST /api/ai/generate-blend`, `GET /api/ai/generations/:id` |
| `migrations/versions/0003_ai_tables.py` | Alembic migration for both new tables |
| `knowledge/*.md` | 15 hand-written coffee knowledge documents |
| `scripts/ingest_knowledge.py` | One-time (re-runnable) chunk + embed + insert script |

### Frontend

| File | Purpose |
|------|---------|
| `lib/api/ai.ts` | Typed API client: `generateBlend()`, `getGeneration()` |
| `app/dashboard/owner/blends/new/page.tsx` | New Blend page (form + loader + result) |
| `components/features/RecipePercentageBar.tsx` | Stacked percentage bar with legend |
| `components/features/AIReasoningPanel.tsx` | Profile meters, note dots, feedback pills, reasoning |
| `components/features/GenerationLoader.tsx` | Staged loader with 4 animated steps |

---

## Database changes

### Migration 0003 — `flask db upgrade`

**`knowledge_chunks`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `owner_id` | uuid FK → users | NULL = global; set = owner-private |
| `source_type` | varchar(20) | `DOC`, `BEAN`, `FEEDBACK`, `BLEND` |
| `source_id` | uuid | nullable — points to the originating row |
| `content` | text | plain text chunk |
| `metadata` | jsonb | source filename, chunk index, etc. |
| `embedding` | vector(1536) | text-embedding-3-small output |
| `created_at` | timestamptz | |

Indexes: `owner_id`, `(owner_id, source_type)`, HNSW cosine index on `embedding`.

**`ai_generations`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `owner_id` | uuid FK → users | |
| `kind` | varchar(30) | `GENERATE`, `SUBSTITUTE`, `CHAT`, `FEEDBACK_ANALYSIS` |
| `input` | jsonb | raw request body |
| `retrieved_chunk_ids` | uuid[] | chunks used in this call |
| `raw_output` | text | unvalidated model output |
| `validated_output` | jsonb | null if validation failed |
| `status` | varchar(10) | `OK`, `INVALID`, `ERROR` |
| `model` | varchar(100) | model identifier used |
| `latency_ms` | int | end-to-end LLM call time |
| `error` | text | error message if status ≠ OK |
| `created_at` | timestamptz | |

---

## AI service

`app/services/ai_service.py` is the single point of contact with OpenRouter.

```python
complete_json(messages, schema, model=None, temperature=0.3) -> (dict, latency_ms)
embed(texts: list[str]) -> list[list[float]]
```

Both functions use one `httpx.Client`. Changing the provider or model means editing this one file — no other service imports the HTTP client directly.

**JSON-schema enforcement:** `complete_json` sends `response_format.type = "json_schema"` with the blend schema. If the model returns a markdown-fenced block instead of bare JSON (some providers do this), the fences are stripped before parsing.

**Env vars required:**
```
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openai/gpt-4o-mini        # or any OpenAI-compatible model
OPENROUTER_EMBED_MODEL=openai/text-embedding-3-small
```

---

## Knowledge documents

15 markdown files in `backend/knowledge/`:

| File | Topic |
|------|-------|
| `01-coffee-origins-africa.md` | Ethiopia, Kenya, Rwanda, Tanzania |
| `02-coffee-origins-latin-america.md` | Brazil, Colombia, Guatemala, Peru, Costa Rica |
| `03-coffee-origins-asia-pacific.md` | Indonesia (Sumatra, Java, Sulawesi, Flores), PNG, India |
| `04-varietals-and-genetics.md` | Typica, Bourbon, SL28/34, Gesha, Heirloom, Robusta |
| `05-processing-methods.md` | Washed, natural, honey, wet-hulled, anaerobic |
| `06-roast-levels-and-effects.md` | Light → dark, numeric adjustments, roast × method table |
| `07-blending-principles.md` | Three-role framework, weighted average formula, conflict points |
| `08-espresso-blend-archetypes.md` | 6 reference archetypes (Italian, chocolate, fruit-forward, etc.) |
| `09-filter-blend-archetypes.md` | Pour-over, milk blend, oat milk pairing, seasonal |
| `10-flavor-wheel-reference.md` | Acidity/body/sweetness descriptors, note → axis mapping |
| `11-brew-methods-and-extraction.md` | Espresso, filter, cold brew, french press, moka pot |
| `12-acidity-body-sweetness-targets.md` | Numeric targets by style, drinker preference, milk pairing |
| `13-blend-validation-rules.md` | Hard rules, retry logic, JSON schema definition |
| `14-feedback-loop-and-taste-preferences.md` | How constraints are derived, honesty requirements |
| `15-blend-naming-and-description.md` | Copy guidelines: good/bad examples for name, description, reasoning |

### Ingesting the documents

After running `flask db upgrade` (migration 0003):

```bash
cd backend
python -m scripts.ingest_knowledge
```

This reads each `.md` file, splits it into ~400-token chunks with 50-token overlap, embeds each chunk via OpenRouter, and inserts rows with `owner_id = NULL`. Re-running is safe — existing rows for each file are deleted before reinsertion.

---

## RAG service

`app/services/rag_service.py`

```python
retrieve(query_text, owner_id, top_k=8) -> list[KnowledgeChunk]
index_feedback(owner_id, blend_id, comment, rating_context) -> KnowledgeChunk
index_bean(bean) -> KnowledgeChunk
```

**The ownership filter is non-negotiable:**

```sql
WHERE (owner_id IS NULL OR owner_id = :owner_id)
ORDER BY embedding <=> CAST(:embedding AS vector)
LIMIT :top_k
```

This single clause is what stops one owner's private feedback from appearing in another owner's prompt. It is baked into every retrieval query and cannot be bypassed by any caller.

---

## Generation pipeline

`app/services/blend_generation_service.py` — `generate_blend(request, owner_id)`

```
1. Load taste_adjustments from owner_profiles
2. SQL: candidate beans (AVAILABLE | LOW_STOCK, stock ≥ 0.5 kg, optional price cap)
3. RAG: retrieve top-8 chunks scoped to this owner
4. Build system + user messages (candidates table, constraints, knowledge, task)
5. Call LLM via ai_service.complete_json with JSON schema
6. Validate with Pydantic (LLMBlendOutput):
   - 2–5 components, percentages sum = 100 exactly, no duplicates
   - All bean IDs in candidate set, min 5% per bean, max 85%
   - Text lengths within bounds, no HTML
7. On failure: append errors, retry once
8. On second failure: log status=INVALID, raise ValueError → 422
9. Compute weighted acidity/body/sweetness from stored bean values
10. Heuristic note estimation (chocolate, caramel, fruitiness, nuttiness, florality)
11. Log to ai_generations (always, regardless of outcome)
12. Return { generation_id, draft }
```

The computed profile (step 9) is deterministic arithmetic — it never comes from the LLM. The estimated notes (step 10) are rule-based heuristics from origin, roast, and processing. Both are clearly labelled in the UI.

---

## API endpoints

### `POST /api/ai/generate-blend`

**Auth:** `OWNER` role required  
**Rate limit:** 10 requests per minute per user  

**Request body:**
```json
{
  "prompt": "Bold espresso, dark chocolate, low acidity, heavy body",
  "style": "espresso",
  "preset_id": null,
  "max_price_per_kg": 180.00
}
```

**Response 200:**
```json
{
  "generation_id": "b1f0a3c2-...",
  "draft": {
    "blend_name": "Graveyard Shift",
    "description": "A bold, chocolate-forward espresso blend...",
    "recipe": [
      { "coffee_bean_id": "uuid-a", "name": "Brazil Santos", "origin": "Brazil", "percentage": 55 },
      { "coffee_bean_id": "uuid-b", "name": "Gayo Aceh", "origin": "Indonesia", "percentage": 30 },
      { "coffee_bean_id": "uuid-c", "name": "Ethiopia Yirgacheffe", "origin": "Ethiopia", "percentage": 15 }
    ],
    "profile": {
      "computed": { "acidity": 3.9, "body": 8.4, "sweetness": 6.7 },
      "estimated": { "chocolate": 8.2, "caramel": 7.1, "fruitiness": 3.4, "nuttiness": 6.5, "florality": 2.1 }
    },
    "reasoning": "Brazil Santos at 55% provides...",
    "applied_feedback": ["Reduced acidity: your last two milk-based tests were rated too acidic."]
  }
}
```

**Response 422:** Permanent validation failure after one retry  
**Response 503:** Network/API error reaching OpenRouter

### `GET /api/ai/generations/:id`

**Auth:** `OWNER` role required. Ownership enforced — another user's ID returns 404.

---

## Frontend

### `/dashboard/owner/blends/new`

Client component. Three sections:

**1. Form**
- Freetext prompt (`<textarea>`, max 1000 chars)
- One-click example prompts as chips
- Brew-style selector (espresso / milk / filter) with hints
- Optional max price per kg

**2. Staged loader** (`GenerationLoader`)
Four animated stages shown while the fetch is in flight:
- Retrieving coffee knowledge…
- Selecting candidate beans…
- Building your recipe…
- Validating the blend…

**3. Recipe result** (shown after success)
- Blend name + description
- `RecipePercentageBar` — stacked coloured bar with legend
- Bean details table (name, origin, percentage)
- `AIReasoningPanel`:
  - **Computed profile** — three `ProfileMeter` bars for acidity / body / sweetness, labelled "(weighted average of bean values)"
  - **Estimated notes** — dot grid for chocolate, caramel, fruitiness, nuttiness, florality, labelled "(AI estimate — directional only)"
  - **Applied feedback** pills — only shown if adjustments were applied
  - **Why this blend** — the LLM reasoning text
- Save CTA → `/dashboard/owner/blends/save?generation_id=...`

### New components

**`RecipePercentageBar`** (`components/features/RecipePercentageBar.tsx`)  
Renders a segmented horizontal bar proportional to blend percentages. Five brand colours cycle for up to 5 beans. Includes a labelled legend below.

**`AIReasoningPanel`** (`components/features/AIReasoningPanel.tsx`)  
Self-contained panel showing the full profile breakdown. Computed profile uses `FLAVOR_AXES` from `product.config.ts` to stay in sync with the backend scale. Estimated notes use a 10-dot grid to make the "directional, not measured" nature visually obvious.

**`GenerationLoader`** (`components/features/GenerationLoader.tsx`)  
Advances through 4 stages every 2 seconds while `active=true`. Resets when generation completes.

### Typed API client

`lib/api/ai.ts` exports:
- `generateBlend(body)` → `Promise<GenerateBlendResponse>`
- `getGeneration(id)` → `Promise<AIGeneration>`

Both go through the existing `apiFetch` proxy so the Bearer token is attached server-side.

---

## Running Phase 3 locally

```bash
# 1. Apply the migration
cd backend
flask db upgrade

# 2. Ingest knowledge documents (requires OPENROUTER_API_KEY in .env)
python -m scripts.ingest_knowledge

# 3. Start the backend (Phase 2 seed must already be applied)
flask run --port 5000

# 4. Start the frontend
cd ../frontend
npm run dev
```

Then navigate to `/dashboard/owner/blends/new` and enter a prompt.

---

## Exit criteria status

| Criterion | Status |
|-----------|--------|
| Demo prompt returns a recipe whose percentages sum to 100 using only available beans | ✅ Enforced by `LLMBlendOutput` validator + candidate ID check |
| Invalid model output is rejected, retried once, then returns 422 and logs INVALID | ✅ Two-attempt loop in `blend_generation_service.py` |
| A forced invalid bean ID never reaches the response | ✅ Every ID checked against the candidate set before accepting output |
| Retrieval never returns another owner's rows | ✅ `owner_id IS NULL OR owner_id = :owner_id` in every RAG query |

---

## What Phase 4 needs from Phase 3

- `generation_id` stored on a saved blend via `source_generation_id FK → ai_generations`
- `draft.recipe` used to pre-populate the `BlendRecipeEditor` on the Save page
- `blend_generation_service.generate_blend` called again with `preset_id` once presets exist
