# Improvements Plan

Planning doc only — **nothing here is implemented yet.** Tanishk will say when to
build each item. Everything is scoped to run in **testing mode** (no Clerk), the way
the project runs today.

Last updated: 2026-08-04

---

## Item 1 — Organizations tab (create org → work inside it)

### What Tanishk wants
A real **Organizations** area where a user can:
1. Enter an **organization name** and create an organization.
2. See a list of their organizations.
3. **Select / enter an organization**, and create **projects inside that organization**.
   Projects belong to the chosen org; switching org changes which projects you see.

Different organizations can each put their own name and keep their projects separate.

### How it works today (the gap)
- The backend is already **multi-tenant**: every table has `organization_id`, protected
  by Postgres **Row-Level Security (RLS)** keyed on `app.tenant_id`. So data isolation
  per-org already exists at the DB level.
- BUT there is **no "create organization" endpoint**. `organizations.py` only has
  `GET/PATCH /organizations/me` — it reads/updates the *current* org, assumed to come
  from the auth token (Clerk org id).
- In **testing mode**, the org is just the `X-Test-Tenant-Id` header, and the frontend
  hardcodes a **single** `DEV_TENANT_ID` (`auth-sync.tsx`, `client.ts`). So today there
  is effectively **one fixed organization** and no UI to create or switch orgs.

### Plan to build it

**Backend**
- [ ] `POST /organizations` — create an org from a name (generates `slug`, a tenant UUID,
      and — in testing mode — a synthetic `clerk_org_id` like `test_<slug>`). Returns the
      new org's `id` (this becomes the tenant id the frontend sends).
- [ ] `GET /organizations` — list orgs the current demo user can access. In testing mode,
      "access" = a simple membership/owner table keyed by `X-Test-User-Id`, OR (simplest)
      list all orgs created in testing mode. Decide during build (see Open Questions).
- [ ] Keep existing `GET/PATCH /organizations/me` for the *active* org.
- [ ] Guard: creating an org must bypass RLS insert (orgs table already has RLS disabled —
      confirmed in `0001_initial_schema.py`), so this is safe.

**Frontend**
- [ ] New **Organizations** page/tab: form to create an org (name), list of orgs, and a
      "use this organization" action.
- [ ] Store the **selected org id** (e.g. in `localStorage`) and make `client.ts` /
      `auth-sync.tsx` send it as `X-Test-Tenant-Id` INSTEAD of the hardcoded
      `DEV_TENANT_ID`. This is the key wiring change — one place, both files.
- [ ] Projects page already scopes by tenant via RLS, so once the header carries the
      selected org, "projects inside this org" works automatically.
- [ ] Org switcher in the top nav (dropdown) so the user can move between their orgs.

**Data model** — no schema change needed for the core (org table exists). Optional:
- [ ] A lightweight `testing_memberships` concept (user_id → org_id) if we want each demo
      user to only see their own orgs. Skip for v1 if "all testing orgs visible" is fine.

### Acceptance (how we'll verify)
- Create two orgs "Acme Legal" and "Globex" → each shows only its own projects.
- Create a project under Acme → it does NOT appear when Globex is selected (RLS proof).
- Switch org in the nav → project list changes accordingly.

### Open questions (decide at build time)
- Should each demo user see **only orgs they created**, or **all** testing orgs?
- Org switching: dropdown in nav, or a dedicated "enter organization" landing step?

---

## Item 2 — Surface Phase 6 (semantic) inside Findings / Fixes tab

### What Tanishk wants
Phase 6 (embeddings + semantic search) currently has **no UI** — it lives behind the
`/search` API only. Instead of a separate search page, the semantic capability should
**show up in the Findings / Fixes tab** so it's visibly part of the review flow.

### How it works today
- Phase 6 backend is done and verified: embed-on-upload → `clause_embeddings` (Postgres)
  + Qdrant, and `HybridRetriever` (vector + Postgres full-text, RRF-fused), exposed as
  `GET /projects/{id}/search`.
- The **Findings page** (`findings/page.tsx`) lists issues with tabs (All / Pending /
  Approved / Rejected) and a **detail sheet** (`finding-detail-sheet.tsx`) that already
  fetches and shows the clause text a finding is pinned to.
- Nothing in that flow uses embeddings yet.

### Plan — three ways Phase 6 can enrich Findings/Fixes (pick during build)

**Option A — "Similar clauses" panel in the finding detail sheet (recommended)**
- [ ] When a reviewer opens a finding, call `/search` (or a new
      `/findings/{id}/similar`) using the finding's clause text as the query, scoped to
      the org's **clause library** and/or the current contract.
- [ ] Show a "Related / similar clauses" section: ranked matches with score + source.
- [ ] Value: reviewer instantly sees precedent — "how has this clause been handled
      before" — which is exactly the semantic layer's point.

**Option B — Semantic search box on the Findings page**
- [ ] Add a search input at the top of Findings: type a question, jump to the most
      relevant clause/finding. Uses `/search` directly.
- [ ] Lightweight; makes Phase 6 immediately clickable.

**Option C — Semantic-powered dedup / grouping of findings**
- [ ] Use embeddings to group near-duplicate findings ("this issue appears in 3 clauses")
      more intelligently than the current text dedup (`findings-dedup.ts`).
- [ ] Higher effort; improves the existing list quality rather than adding a new panel.

**Recommendation:** start with **Option A** (most visible, most useful, fits the detail
sheet that already exists), optionally add **Option B** as a quick win.

> **STATUS — Option A v1 DONE (2026-08-04).** "Related clauses in this contract" panel
> is built and shipped:
> - Backend: `GET /projects/{id}/findings/{flag_id}/similar` — uses the finding's clause
>   text as the query, runs the Phase 6 HybridRetriever scoped to the project, excludes
>   the finding's own clause, returns ranked related clauses. Gated on ENABLE_EMBEDDINGS.
>   (`app/api/v1/endpoints/tasks.py`)
> - Frontend: `useSimilarClauses` hook + a violet "Related clauses in this contract" panel
>   in the finding detail sheet (`finding-detail-sheet.tsx`). Fails soft when semantic
>   search is off. Shows each match's text + similarity %.
> - Tests: `tests/integration/test_similar_clauses_api.py` (3 tests, retriever mocked —
>   ZERO API calls). Full suite 76 passed. Frontend typechecks + builds clean.
> - NOT yet done: a live in-app screenshot (deferred per "no API calls for testing").
>   The user will verify live when ready.
>
> **Follow-ups still open for Item 2:**
> - Option A "against the library" (precedent) — needs the clause library migrated from
>   the OLD voyage path to the Phase 6 pipeline (see note below). NOT done.
> - Option B (semantic DETECTION — change which findings appear, fix false "missing
>   clause" positives). This is the part that makes the finding COUNT change. NOT started.

### Backend work
- [x] `GET /projects/{id}/findings/{flag_id}/similar` endpoint that wraps `HybridRetriever`
      with the finding's clause as the query. **DONE.**
- [ ] Ensure library entries are embedded on the Phase 6 pipeline. **IMPORTANT DISCOVERY:**
      there are currently TWO parallel embedding systems in the codebase:
        - **OLD**: `library_service.py` embeds clause-library entries via
          `voyage_client.embed_texts` into a PER-TENANT Qdrant collection
          (`tenant_collection_name`). Depends on the Voyage key (placeholder) — so library
          precedent search does NOT work today.
        - **NEW (Phase 6)**: contract clauses embed via NVIDIA/local into the
          dimension-scoped `contract_chunks_{dim}` collection. This is what works.
      To do "similar from library", **migrate `library_service` onto the Phase 6 pipeline**
      (embedding_service / HybridRetriever), then the library becomes searchable with the
      same provider. Until then, Option A only does "within this contract".

### Acceptance
- Open a finding → see a "Similar clauses" panel populated with ranked, relevant matches.
- The matches are semantically correct (paraphrases surface, not just keyword hits).

### Open questions
- Similar-to-WHAT by default: the org's clause **library** (precedent), the **same
  contract** (internal consistency), or both?
- New dedicated endpoint vs. reuse `/search` from the frontend?

---

## Cross-cutting notes
- All of this stays in **testing mode** — no Clerk. Clerk integration is a separate,
  later decision.
- Follow the established workflow: superpowers brainstorm → plan → **TDD** (RED/GREEN),
  build against mocks first, minimal live API calls. Keep the pytest suite credit-free
  (`ENABLE_EMBEDDINGS` is forced false in tests).
- Nothing is pushed to GitHub automatically — only when Tanishk says so.

## Suggested build order
1. **Item 1 (Organizations)** first — it's foundational (projects live inside orgs) and
   independent of Phase 6.
2. **Item 2 (Phase 6 in Findings)** second — needs the library-embed gap resolved.
