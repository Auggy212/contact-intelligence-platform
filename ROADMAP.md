# ContractIQ — Implementation Roadmap: PoC → Industry Grade

> **Status:** Phase 1 (Proof of Concept) complete. Phases 2–5 planned.
> **Audience:** Engineering team + company stakeholders (handover document).
> **Product:** ContractIQ — AI-powered contract review for Indian law (multi-tenant SaaS).
> **Last updated:** 2026-07-15

---

## How to read this document

Each phase is **independently shippable** and ends with a concrete **exit criterion** — a measurable gate that must pass before the next phase starts. Horizons are indicative for a small team (2–3 backend, 1 frontend) and assume the previous phase is stable.

The phases are numbered in **dependency order, not arbitrary priority**:
- Ingestion + embeddings (Phase 2) come first because everything after depends on clean, semantically-indexed text.
- Guardrails (Phase 3) ship *with* the LLM, never after — an ungrounded legal AI is a liability from day one.
- Scale (Phase 4) precedes the enterprise security push (Phase 5) because compliance controls are cheaper to build into a mature, observable platform than to retrofit.

**Core design principle carried through every phase:** *The AI never decides — it surfaces and explains; a human approves.* This is already how Phase 1 works. It is preserved deliberately: it is both the right ethical posture for legal work and the compliance story (human oversight) that regulators and enterprise buyers expect.

---

## Table of contents

1. [Baseline: What Phase 1 actually is](#baseline-what-phase-1-actually-is)
2. [Phase 2 — Ingestion & Semantic Understanding](#phase-2--ingestion--semantic-understanding)
3. [Phase 3 — LLM Reasoning with Guardrails](#phase-3--llm-reasoning-with-guardrails)
4. [Phase 4 — Scale, Reliability & Availability](#phase-4--scale-reliability--availability)
5. [Phase 5 — Security, Compliance & Enterprise Readiness](#phase-5--security-compliance--enterprise-readiness)
6. [Non-functional requirements matrix](#non-functional-requirements-matrix)
7. [Sequencing & recommended next sprint](#sequencing--recommended-next-sprint)
8. [Research references](#research-references)

**Part II — Detailed AI Build Plan** *(semantic understanding, chunking, embeddings, RAG bot, LangGraph)*
9. [Phase 6 — The Pluggable Semantic Foundation](#phase-6--the-pluggable-semantic-foundation)
10. [Phase 7 — Semantic Analysis](#phase-7--semantic-analysis-retire-the-regex-ceiling)
11. [Phase 8 — RAG Chatbot (project- and organization-scoped)](#phase-8--rag-chatbot-project--and-organization-scoped)
12. [Phase 9 — LLM Reasoning + Guardrails](#phase-9--llm-reasoning--guardrails-deep-analysis)
13. [Phase 10 — Clause Library & Precedent Search](#phase-10--clause-library--precedent-search)
14. [Phase 11 — Agentic Orchestration (LangGraph)](#phase-11--agentic-orchestration-langgraph)

---

## Baseline: What Phase 1 actually is

An honest read of the codebase today. Naming both the strengths and the gaps is what makes the roadmap credible.

### Already solid (the foundation to build on)

| Area | What exists |
|---|---|
| **Tenancy** | Multi-tenant SaaS with PostgreSQL row-level security (per-org isolation enforced at the DB) |
| **Async backend** | FastAPI (async) + Celery job queue (Redis broker); MinIO/S3 object storage |
| **Parsing** | DOCX + born-digital PDF parsing, clause extraction, OOXML tracked-change detection |
| **Analysis** | 4 deterministic agents (Template Comparison, Vendor Diff, Law Validator, Checklist Validator) |
| **Outputs** | Deterministic fix suggestions, plain-English findings, audit log, PDF export |
| **Platform** | Stripe billing, Clerk auth, ~410 tests, Docker-based local infra (db/redis/minio/qdrant) |
| **Foresight** | Agents written with explicit "upgrade path" seams for embeddings + LLM |

### Where it is still a PoC (what the roadmap replaces)

| Gap | Impact |
|---|---|
| **Rules & regex only** | No semantic understanding; brittle on phrasing the rules didn't anticipate |
| **No OCR** | Scanned or photographed contracts yield no text at all |
| **No embeddings / RAG** | Qdrant is provisioned but unused; matching is text-similarity, not meaning |
| **No LLM verification** | Cannot explain or reason about novel clauses |
| **Single-node infra** | No autoscaling, HA, or DR story |
| **No formal security posture** | SOC 2 / DPDP / GDPR not yet addressed |

**The right framing:** Phase 1 proved the *workflow* and the *data model*. Phases 2–5 replace the narrow engine with real intelligence and wrap it in enterprise-grade operations.

---

## Phase 2 — Ingestion & Semantic Understanding

**Horizon:** ~8–12 weeks · **Theme:** stop being brittle.

Two upgrades unlock everything after them: **read any document** (OCR for scans/photos) and **understand meaning, not just wording** (embeddings).

### 2.1 Document AI pipeline for scanned contracts (OCR)

**Problem:** Today only born-digital DOCX/PDF text is read (`app/parsers/pdf_parser.py` uses PyMuPDF text extraction). A scanned or photographed contract produces empty text.

**Solution:** Add an OCR + layout stage that classifies each document and routes only image-based files through Document AI, preserving tables and reading order.

**Tasks**
- [ ] Add a "needs OCR" classifier in the parse pipeline: detect image-only / low-text-density pages (heuristic: text-char count per page area).
- [ ] Integrate an OCR + layout provider behind an interface (`OcrProvider`) so it's swappable:
  - **Cloud (fastest to ship, best on structured docs):** Azure Document Intelligence (`prebuilt-layout` / `prebuilt-contract`), or AWS Textract.
  - **Self-hosted (data stays in VPC, no per-page cost):** Tesseract + docTR, optionally LayoutLMv3 / DiT for layout.
- [ ] Preserve table structure (row/column) and reading order into the existing `parsed_clauses` model.
- [ ] Store OCR confidence per block; flag low-confidence regions for reviewer attention.
- [ ] Route OCR jobs through Celery (new `ocr` queue) so they don't block digital parsing.

**Key files:** `app/parsers/pdf_parser.py`, `app/parsers/clause_extractor.py`, `app/workers/parse_tasks.py`, `app/services/document_service.py`.

**Tech:** Azure Document Intelligence · AWS Textract · Tesseract / docTR (self-host) · LayoutLMv3

### 2.2 Semantic clause matching (RAG foundation)

**Problem:** Matching is text-similarity based — "IP vests in the vendor" won't match a template clause phrased differently.

**Solution:** Embed clauses with a legal-tuned model; match by meaning. Activate the already-provisioned Qdrant.

**Tasks**
- [ ] Add an `EmbeddingProvider` interface; first implementation = Voyage `voyage-law-2` (legal-domain embeddings).
- [ ] Embed template clauses (File A) and index in Qdrant per tenant/collection.
- [ ] Replace `ValueExtractor` / template-match internals in `clause_analyzer.py` and `template_comparison.py` with **hybrid retrieval**: BM25 (keyword) + vector (semantic), reciprocal-rank-fused.
- [ ] Cache embeddings (content-hash keyed) so re-analysis is cheap.
- [ ] Wire the `embedding` column already stubbed in `documents.py` (`embedding=None` today).

**Tech:** Voyage `voyage-law-2` · Qdrant · hybrid BM25 + vector retrieval

### 2.3 ML clause typing

**Problem:** Clause-type detection is regex-based (`ClauseType` enum + patterns).

**Solution:** Embedding classifier over the standard legal taxonomy (indemnity, IP, liability, termination, data protection, confidentiality, jurisdiction, payment…), improving every downstream agent.

**Tasks**
- [ ] Build a labelled clause-type dataset (CUAD-style categories + the 6 Indian-law checklist domains).
- [ ] Train a lightweight classifier: clause embedding → linear/logistic head.
- [ ] Fall back to the existing regex rules when classifier confidence is low (belt-and-braces).

**Tech:** embedding + linear head · CUAD-style labels

### 2.4 Gold set & evaluation harness (quality gate)

**Problem:** Model changes are currently judged by eye. That is unacceptable for a legal tool.

**Solution:** Expand the existing P/R/F1 harness (`scripts/run_eval.py`, `tests/eval/gold_set.json`) into a versioned benchmark.

**Tasks**
- [ ] Grow the gold set beyond `Test_Contracts_new` — add real-world-shaped edge cases.
- [ ] Report precision / recall / F1 **per clause type** and per agent.
- [ ] Add a regression gate in CI: a model change may not drop F1 below the recorded baseline.
- [ ] Track cross-field false positives explicitly (a known Phase 1 failure mode already fixed once).

**Tech:** P/R/F1 per clause type · regression gate in CI

### ✅ Phase 2 exit criterion
> A scanned contract flows end-to-end (OCR → clauses → findings); semantic matching beats the rule engine on the benchmark by a **measured margin**, with **no regression** on the current gold set.

---

## Phase 3 — LLM Reasoning with Guardrails

**Horizon:** ~10–14 weeks · **Theme:** reasoning without liability.

Introduce an LLM to **explain, reason, and handle novel clauses** the rules can't — wrapped in the trust controls a legal product requires. Intelligence without guardrails is a liability here, not a feature.

### 3.1 RAG-grounded clause analysis

**Solution:** Retrieve relevant statute passages + template clauses, then have Claude reason over *grounded* context — never free-floating generation. Every claim cites its source clause and law section.

**Tasks**
- [ ] Build a retrieval layer over: (a) the tenant's template clauses, (b) the bundled Indian-law corpus (ICA 1872, IT Act, MSME, CPA 2019, etc.).
- [ ] Add an `LlmProvider` interface; first implementation = Claude (latest model).
- [ ] Prompt design: the model must return findings **with citations** (source clause id + law section). Reject outputs missing citations.
- [ ] Only invoke the LLM for clauses the deterministic + embedding path flagged as *novel / low-confidence* (see 3.4 routing).

**Tech:** Claude (latest) · retrieval-grounded · citation-required output

### 3.2 Hallucination guardrails

**Solution:** Validate 100% of model output where a wrong answer causes harm.

**Tasks**
- [ ] **Grounding check:** verify each cited clause/section actually exists in the retrieved context; drop or downgrade unsupported claims.
- [ ] **Confidence scoring:** surface an explicit "the AI is unsure — review carefully" state instead of a confident guess.
- [ ] **Ensemble reconciliation:** rules and LLM cross-check each other; disagreement is surfaced, not silently resolved.
- [ ] Log every LLM claim + its grounding result for audit and eval.

**Tech:** grounding verification · output validation · ensemble reconciliation

### 3.3 Human-in-the-loop by design

**Solution:** Every AI finding stays a *suggestion* a lawyer approves or rejects — already the Phase 1 model (`reviewer_status` on `clause_flags`).

**Tasks**
- [ ] Capture approve/reject feedback as training signal.
- [ ] Feed accepted/rejected findings back into retrieval ranking and prompt few-shot examples over time.

**Tech:** reviewer approve/reject · feedback loop

### 3.4 Model routing & cost control

**Solution:** Cheap deterministic path for the easy 80%; LLM only for genuinely novel clauses.

**Tasks**
- [ ] Tiered router: rules → embeddings → LLM, escalating only on low confidence.
- [ ] Prompt caching (cache the statute corpus + template context across calls).
- [ ] Per-tenant token budgets + usage metering (extends existing billing).

**Tech:** tiered routing · prompt caching · per-tenant budgets

### ✅ Phase 3 exit criterion
> The LLM path improves recall on novel clauses on the benchmark; **every AI claim is source-cited**; and a measured hallucination rate is **at or near zero** on the eval set.

---

## Phase 4 — Scale, Reliability & Availability

**Horizon:** ~8–12 weeks · **Theme:** survive real load and real failure.

An enterprise buyer's first questions are "what's your uptime?" and "what happens when a node dies?" — this phase gives real answers.

### 4.1 Horizontal, autoscaling deployment

**Tasks**
- [ ] Containerise API + workers; deploy to Kubernetes.
- [ ] Horizontal Pod Autoscaler on **Celery queue depth** (not just CPU) so analysis backlog drains automatically.
- [ ] Move to managed PostgreSQL with **read replicas**; keep RLS.
- [ ] Ensure workers are **stateless** (fix any remaining per-process assumptions from the Windows `--pool=solo` dev setup).

**Tech:** Kubernetes · HPA on queue depth · managed Postgres + replicas

### 4.2 High availability & disaster recovery

**Tasks**
- [ ] Multi-AZ deployment; health checks + graceful degradation.
- [ ] Automated backups with **tested restore** (a backup you haven't restored is not a backup).
- [ ] Define and document **RPO/RTO**; point-in-time recovery (PITR) for Postgres.
- [ ] Publish an uptime **SLO**.

**Tech:** multi-AZ · PITR backups · RPO/RTO defined

### 4.3 Observability & resilience

**Tasks**
- [ ] Metrics, distributed tracing, structured logs (the app already uses `structlog`).
- [ ] Retries with backoff + **dead-letter queues** for failed analyses.
- [ ] Harden **idempotency** of jobs (a known Phase 1 weak spot — inline vs Celery paths, duplicate task handling).

**Tech:** OpenTelemetry · Prometheus/Grafana · DLQ + idempotency

### 4.4 CI/CD & environments

**Tasks**
- [ ] Staging/prod parity; infrastructure-as-code (Terraform) so environments are reproducible.
- [ ] Blue-green or **canary** releases.
- [ ] Wire the **eval harness (2.4) as a release gate** — no deploy if F1 regresses.

**Tech:** IaC (Terraform) · canary deploys · eval gate

### ✅ Phase 4 exit criterion
> The platform autoscales under a load test, survives a simulated node/AZ failure, restores from backup within the stated RTO, and ships behind a canary pipeline.

---

## Phase 5 — Security, Compliance & Enterprise Readiness

**Horizon:** ~12–16 weeks · **Theme:** what lets a legal department actually sign.

Contracts are among the most sensitive documents a company holds. This phase clears procurement and security review.

### 5.1 Compliance: SOC 2 Type II · GDPR · India DPDP

**Tasks**
- [ ] Formal control set + **evidence collection** (access reviews, change management, incident response).
- [ ] Data-processing agreements; **data residency in India** for DPDP Act 2023 compliance.
- [ ] Retention & deletion policies; right-to-erasure workflows (GDPR/DPDP).
- [ ] AI-specific governance in the direction of **ISO 42001** (model cards, eval records, human-oversight evidence).

**Tech:** SOC 2 Type II · DPDP Act 2023 · GDPR · ISO 42001

### 5.2 Security: data protection & isolation

**Tasks**
- [ ] Encryption in transit (TLS) and at rest (KMS-managed keys).
- [ ] Secrets management (no secrets in env files in prod); least-privilege IAM.
- [ ] **VPC-isolated inference** so contract text never leaves the tenant boundary (self-hosted OCR/embeddings option from Phase 2 pays off here).
- [ ] RBAC + SSO/SAML for enterprise identity; per-tenant audit trails (extends existing audit log).

**Tech:** KMS / encryption · VPC-isolated inference · RBAC + SSO/SAML

### 5.3 Usability: reviewer-grade UX

**Tasks**
- [ ] **Redline diff view** (template vs draft vs vendor, side by side with change highlighting).
- [ ] **Bulk review** + keyboard-driven triage for high-volume reviewers.
- [ ] Saved **playbooks** (per-org checklist rule sets, reusable across projects).
- [ ] Extend the plain-English "what changed / why it matters / what to do" framing everywhere.
- [ ] **Harden the Verify document renderer** (see "Known limitations" below).

**Tech:** redline diff · bulk actions · playbooks

#### Known limitations — Verify document preview (current Phase 1 behaviour)

The Verify tab renders the user's **original uploaded document, byte-for-byte**, in the browser using the **`docx-preview`** library (`renderAsync()` in `frontend/src/components/verify/document-verify-view.tsx` — the only file using it). Two limitations to address here:

- **No virtualization / large-document performance.** `docx-preview` renders the *entire* document into the DOM at once — there is no lazy-loading or page windowing. Typical contracts (1–20 pages) render instantly. A **~50-page document renders successfully but with a noticeable delay and higher memory use** — it is near the practical ceiling. Very large (100+ page) or image-heavy documents risk a long freeze or browser-memory exhaustion. Upload is hard-capped at **50 MB** (`_MAX_SIZE_BYTES` in `documents.py`), which bounds the worst case but does not solve it.
  - *Fix (future):* virtualized/paginated rendering — render only the pages in view, mount/unmount on scroll (`IntersectionObserver` or a windowing library). Handles 200+ pages at near-constant memory.
  - *Related cost:* the click-to-highlight logic scans every `<p>/<h1>/…/<td>` node on each click; cost grows linearly with page count (fine today, worth revisiting with virtualization).
- **`.docx` only — PDFs do not preview.** `docx-preview` cannot render PDFs. A PDF is still analyzed correctly (the backend `pdf_parser.py` extracts its text), but its original document will not display in the Verify tab.
  - *Fix (future):* add a second renderer — **`pdf.js`** (Mozilla, client-side/offline) — and branch on the file's mime type (`.docx` → docx-preview, `.pdf` → pdf.js).

### 5.4 Accessibility: WCAG 2.2 AA

**Tasks**
- [ ] Full keyboard operability; visible focus states.
- [ ] Screen-reader semantics (ARIA, landmark regions, table semantics).
- [ ] Verified colour contrast (already enforced in the dark theme — extend and audit).
- [ ] Reduced-motion support (already partially present); add automated a11y checks in CI.

**Tech:** WCAG 2.2 AA · a11y CI checks

### ✅ Phase 5 exit criterion
> The platform passes an external security review and accessibility audit, holds (or is in active audit for) SOC 2 Type II, and satisfies DPDP data-residency for Indian clients.

---

## Non-functional requirements matrix

Every quality attribute, the question a buyer will ask, and where it lands.

| Attribute | The question it answers | Approach | Phase |
|---|---|---|---|
| **Scalability** | "Can it handle 10,000 contracts a day?" | Kubernetes autoscaling on queue depth; stateless workers; read replicas | 4 |
| **Reliability** | "What if an analysis job fails?" | Retries + backoff, dead-letter queues, idempotent jobs, tracing | 4 |
| **Availability** | "What's your uptime SLA?" | Multi-AZ, health checks, graceful degradation, published SLO | 4 |
| **Recoverability** | "What if data is lost?" | Automated backups, tested restore, defined RPO/RTO, PITR | 4 |
| **Security** | "Where does our contract text go?" | Encryption everywhere, VPC-isolated inference, RBAC, SSO/SAML | 5 |
| **Compliance** | "Are you SOC 2 / DPDP compliant?" | SOC 2 Type II, GDPR, India DPDP residency, ISO 42001 for AI | 5 |
| **Usability** | "Will my lawyers actually use it daily?" | Redline diff, bulk review, playbooks, plain-English findings | 5 |
| **Accessibility** | "Does it meet WCAG?" | WCAG 2.2 AA, keyboard-first, screen-reader semantics, a11y CI | 5 |
| **Accuracy** | "How do you know it's right?" | Versioned gold set, P/R/F1 gates, hallucination validation | 2–3 |

---

## The intelligence upgrade, concretely

You asked specifically about OCR and moving beyond rules. Here is how the pipeline evolves.

### Ingestion pipeline

```
Today:    Upload → (digital text only) → Clause extraction → Structured clauses
                    ⚠ scanned/photo docs produce no text

Phase 2:  Upload → Classify (digital vs scanned) → [OCR + layout, scans only]
                 → Clause extraction → Structured clauses
```

### Analysis pipeline — hybrid, not either/or

The industry has converged on **hybrid**: rules for speed and determinism, embeddings for semantic recall, an LLM for reasoning — cross-checking each other. Rules never disappear; they become the fast, auditable floor.

```
Clause
  → Rule engine          (fast, deterministic — the auditable floor)
  → Semantic match       (embeddings — catches meaning regardless of wording)   [Phase 2]
  → LLM reasoning        (novel clauses only, retrieval-grounded)               [Phase 3]
  → Guardrail + reconcile (grounding check, ensemble cross-check)               [Phase 3]
  → Ranked finding + citation
```

**Why hybrid and not "just an LLM":** in a legal product, a confident wrong answer is worse than no answer. Determinism where possible, reasoning where necessary, and a source citation on every claim is what earns a lawyer's trust.

---

## Sequencing & recommended next sprint

**Order rationale (dependency, not preference):**
1. **Phase 2 first** — every later capability depends on clean, semantically-indexed text. An LLM reasoning over garbled OCR is worse than no LLM.
2. **Phase 3 guardrails ship with the LLM, never after** — an ungrounded legal AI is a liability the day it launches.
3. **Phase 4 before Phase 5** — security/compliance controls are cheaper to build into a mature, observable platform than to retrofit.

**Deliberate exception:** a few Phase 5 items — verified colour contrast, human-in-the-loop review, audit logging — already exist in Phase 1. That's intentional. The cheapest compliance is designed in from the start, and this codebase already has some of it.

### Recommended next sprint (concrete starting point)
1. **Stand up the evaluation harness as a hard benchmark** (Phase 2.4) — makes every future claim measurable.
2. **Wire in OCR for scanned PDFs** (Phase 2.1) — removes the most visible gap a buyer notices in a demo.

The first makes progress provable; the second closes the most obvious hole. Together they are a self-contained, demoable sprint that de-risks the whole roadmap.

---

## Research references

Current (2026) sources informing this plan:

- [Frontiers — LLMs for clause extraction, classification & summarization (2026)](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2026.1782405/full)
- [arXiv — Metadata extraction with LLMs](https://arxiv.org/html/2510.19334v1)
- [ACM ICAIL — RAG with vector stores & knowledge graphs for legal knowledge](https://dl.acm.org/doi/10.1145/3769126.3769215)
- [Microsoft — Azure Document Intelligence: contract & OCR extraction](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/contract?view=doc-intel-4.0.0)
- [LlamaIndex — Best legal OCR software (2026)](https://www.llamaindex.ai/insights/best-legal-ocr-software)
- [Maxim — AI guardrails implementation guide (2026)](https://www.getmaxim.ai/articles/the-complete-ai-guardrails-implementation-guide-for-2026/)
- [TechAhead — SOC 2 for AI systems (2026)](https://www.techaheadcorp.com/blog/soc-2-ai-systems-controls/)
- [GuardionAI — LLM compliance: ISO 42001, EU AI Act, SOC 2, GDPR (2026)](https://guardion.ai/blog/llm-compliance-guide-iso-42001-eu-ai-act-soc2-gdpr-2026)
- [arXiv — Assessing reliability of AI legal research tools (hallucination)](https://arxiv.org/pdf/2405.20362)

---

# Part II — Detailed AI Build Plan (Semantic + RAG + Agentic)

> **For agentic workers:** built with the `superpowers` methodology — brainstorm → design → decomposed plan. Each task below is a small, independently-testable unit (write failing test → verify fail → implement → verify pass → commit).
>
> **Goal:** Evolve ContractIQ from a deterministic rule engine into a semantic, RAG-powered, agentic contract-intelligence platform — an outstanding, industry-grade product that is also a portfolio showpiece.
>
> **Architecture:** A pluggable AI provider layer (local models by default, cloud APIs via config) feeds a chunk → embed → vector-index pipeline. That single retrieval layer powers three consumers: (1) semantic clause analysis, (2) a project- and organization-scoped RAG chatbot, and (3) semantic precedent search. A LangGraph state machine orchestrates the existing agents plus new retrieval/reasoning/verification nodes.
>
> **Tech Stack (decisions locked in):** FastAPI · PostgreSQL + pgvector/Qdrant · Celery/Redis · Next.js. **Hybrid/pluggable AI** — **local `sentence-transformers`/BGE embeddings + a FREE hosted-API LLM (Groq / Gemini) by default**; Voyage/Claude/OpenAI (and later AWS Bedrock) via env config. **Direct SDKs** for RAG retrieval+generation, **LangGraph** for agentic orchestration, minimal LangChain.
>
> **Full technical design + AWS deployment ladder:** see `docs/superpowers/specs/2026-07-15-semantic-rag-design.md` (chunking strategy, embedding types, provider config surface, DB schema changes, and the EC2 → ECS/EKS → multi-tenant AWS path deferred until company go-ahead).

## Global constraints (verbatim decisions)

- **Pluggable, not locked to any vendor.** Every AI call goes through a provider interface (`EmbeddingProvider`, `LlmProvider`, `OcrProvider`, `VectorStore`). Defaults: **embeddings = local** (bge, no key/cost), **LLM = free hosted API** (Groq/Gemini — avoids heavy local LLM). Each capability switches **independently** via env var (→ Voyage/OpenAI/Claude/Bedrock) with no code change.
- **Both portfolio AND production quality.** Features must demo impressively *and* be correct, tested, and reliable. No fake data, no placeholder logic.
- **Multi-tenant is already real.** Organizations → Projects → Documents exist today with Postgres row-level security. The RAG bot works at two scopes — **project-scoped** (one project's docs) and **organization-scoped** (all projects in an org) — and RLS guarantees cross-org isolation. Never bypass RLS in retrieval.
- **Grounded or nothing.** Every LLM/bot answer cites the exact clause/section it used. No citation → the claim is dropped or marked low-confidence.
- **Human-in-the-loop preserved.** The AI surfaces and explains; a human approves. Never auto-apply changes to a contract.

---

## Phase 6 — The Pluggable Semantic Foundation

**Horizon:** ~6–10 weeks · **Theme:** one retrieval layer to power everything.

This is the keystone. Chunking + embeddings + vector search built *once*, behind interfaces, consumed by analysis, the bot, and precedent search.

### File mapping (before tasks)

| File | Responsibility |
|---|---|
| `backend/app/ai/providers/base.py` | `EmbeddingProvider`, `LlmProvider`, `OcrProvider` abstract interfaces |
| `backend/app/ai/providers/local.py` | Local impls: sentence-transformers/BGE embeddings, Ollama LLM |
| `backend/app/ai/providers/cloud.py` | Cloud impls: Voyage/Claude (or OpenAI) — activated by env |
| `backend/app/ai/providers/factory.py` | Reads config → returns the configured provider (the pluggable switch) |
| `backend/app/ai/chunking.py` | Contract-aware chunker (clause/section boundaries, overlap, token budget) |
| `backend/app/ai/vector_store.py` | Wraps Qdrant/pgvector: upsert, hybrid search, per-tenant collections |
| `backend/app/models/embedding.py` | `ClauseEmbedding` / chunk metadata table (chunk_id, project_id, org_id, vector ref) |
| `backend/app/workers/embed_tasks.py` | Celery task: chunk + embed a document after parsing |
| `backend/app/services/retrieval_service.py` | Hybrid (BM25 + vector) retrieval with scope filter (project/org) |

### Tasks

- [ ] **6.1 Provider interfaces + factory.** Define `EmbeddingProvider.embed(texts) -> vectors`, `LlmProvider.complete(prompt, context) -> text`, `OcrProvider.extract(bytes) -> text+layout`. Factory selects impl from `AI_PROVIDER` env (`local` | `cloud`). *Test:* factory returns the right class per env value.
- [ ] **6.2 Local embedding provider.** Wire `sentence-transformers` (e.g. `BAAI/bge-small-en` or a legal model). *Test:* embedding a known sentence returns a stable-dimension vector; two paraphrases score higher cosine than two unrelated sentences.
- [ ] **6.3 Contract-aware chunking.** Chunk by clause/section boundary first, fall back to token-window with overlap; never split mid-sentence. Store chunk → source clause mapping. *Test:* a known contract chunks into the expected clause-aligned pieces; overlap present; no chunk exceeds the token budget.
- [ ] **6.4 Vector store + embedding model/migration.** Activate Qdrant (or pgvector), per-tenant collection naming, `ClauseEmbedding` table + Alembic migration. *Test:* upsert N chunks, query returns them ranked; a different org's collection is not searchable.
- [ ] **6.5 Embed-on-parse Celery task.** After a document parses, enqueue chunk+embed; store vectors with `project_id`/`org_id` metadata. *Test:* uploading a doc results in queryable chunks for that project only.
- [ ] **6.6 Hybrid retrieval service.** BM25 (keyword) + vector (semantic), reciprocal-rank-fused, with a mandatory scope filter (`project_id` or `organization_id`). *Test:* semantic query finds a paraphrased clause a keyword search misses; scope filter never leaks across orgs (RLS + filter double-guard).
- [ ] **6.7 Cloud provider parity.** Implement Voyage/Claude behind the same interface; a config flag swaps them in. *Test:* same retrieval test passes with `AI_PROVIDER=cloud` (skipped in CI without keys).

**Exit:** a document, once uploaded, is chunked + embedded + searchable by meaning within its project and org scope, offline by default, cloud-swappable by config — with cross-org isolation proven by test.

---

## Phase 7 — Semantic Analysis (retire the regex ceiling)

**Horizon:** ~4–6 weeks · **Theme:** meaning, not wording.

Re-point the existing analysis agents at the semantic layer so findings survive rephrasing, and unlock custom rules over *arbitrary* extracted fields (the limitation noted in Phase 2/Checklist).

### Tasks

- [ ] **7.1 Semantic template matching.** In `template_comparison.py`, replace text-similarity matching with retrieval against the template's embedded clauses. *Test:* a reworded-but-equivalent clause is matched to its template counterpart; the benchmark F1 does not regress vs. the rule engine.
- [ ] **7.2 Embedding clause classifier.** Replace regex clause-typing with an embedding + linear-head classifier over the legal taxonomy; low-confidence falls back to the existing rules. *Test:* held-out clauses classify at a recorded accuracy; fallback fires on ambiguous input.
- [ ] **7.3 Semantic field extraction.** Extract arbitrary fields (warranty period, SLA %, renewal term…) via retrieval + LLM extraction, so custom checklist rules can reference fields beyond the current ~7. *Test:* a custom rule over a newly-extractable field ("warranty ≥ 12 months") fires correctly.
- [ ] **7.4 Ensemble reconciliation.** Rules + semantic + (Phase 8) LLM cross-check each other; agreement raises confidence, disagreement is surfaced not hidden. *Test:* a clause all three flag scores highest confidence; a split decision is labelled "review carefully".
- [ ] **7.5 Benchmark gate.** Extend the eval harness (already exists) to score semantic vs. rule paths per clause type; wire as a CI regression gate. *Test:* CI fails if F1 drops below the recorded baseline.

**Exit:** semantic matching measurably beats the rule engine on the benchmark with no regression, and users can write custom rules over fields the engine now extracts semantically.

---

## Phase 8 — RAG Chatbot (project- and organization-scoped)

**Horizon:** ~6–8 weeks · **Theme:** interrogate your contracts.

The standout feature. A grounded chat that answers questions about uploaded documents — scoped to a project first, then a whole organization — reusing the Phase 6 retrieval layer.

### File mapping

| File | Responsibility |
|---|---|
| `backend/app/services/chat_service.py` | RAG orchestration: retrieve → assemble grounded context → LLM → cite |
| `backend/app/api/v1/endpoints/chat.py` | `POST /projects/{id}/chat`, `POST /organizations/{id}/chat`, streaming |
| `backend/app/models/conversation.py` | `Conversation` + `ChatMessage` (scope, messages, citations) |
| `frontend/src/components/chat/chat-panel.tsx` | Chat UI (streaming, citation chips that deep-link to the clause) |
| `frontend/src/lib/hooks/use-chat.ts` | Chat state + streaming client |

### Tasks

- [ ] **8.1 Conversation model + migration.** Store conversations with a `scope` (`project`/`org`), scope id, messages, and per-answer citations. *Test:* messages persist and reload; scope enforced.
- [ ] **8.2 Project-scoped RAG service.** Retrieve top-k chunks from the project's scope, assemble a grounded prompt, call `LlmProvider`, return answer + citations (chunk → clause → document). *Test:* "What is the liability cap?" returns the correct value with a citation to the exact clause; a question the docs don't answer returns "not found in these documents", never a guess.
- [ ] **8.3 Streaming chat API.** Server-sent-events streaming so answers render token-by-token. *Test:* endpoint streams; final message includes citation list.
- [ ] **8.4 Chat UI + citation deep-links.** Chat panel with streaming; clicking a citation chip opens the Verify view highlighted on that clause (reuses existing highlight logic). *Test (manual/e2e):* ask → stream → click citation → correct clause highlights.
- [ ] **8.5 Organization-scoped bot.** Same service, scope = `organization_id`, retrieves across all the org's projects; answers say which contract each fact came from. *Test:* "Which contracts have auto-renewal?" returns the right projects; org B's data never appears for org A (RLS + scope filter).
- [ ] **8.6 Guardrails on chat.** Grounding check (every cited chunk must exist in retrieval), refusal on out-of-scope/legal-advice questions, and a visible confidence indicator. *Test:* a fabricated-citation attempt is caught; out-of-scope question is politely refused.

**Exit:** a user can chat with one project's documents (grounded, cited, streaming), then with their whole organization's contract set — with proven cross-org isolation and no ungrounded answers.

---

## Phase 9 — LLM Reasoning + Guardrails (deep analysis)

**Horizon:** ~6–8 weeks · **Theme:** reason about novel clauses, safely.

(Expands Part I Phase 3 with the pluggable decision.) The LLM handles clauses the rules + embeddings can't, always retrieval-grounded, always cited, always cross-checked.

### Tasks

- [ ] **9.1 Grounded reasoning node.** For clauses the deterministic + semantic paths flag as novel/low-confidence, retrieve statute + template context and have the `LlmProvider` reason with citation-required output. *Test:* a novel clause gets a reasoned, cited finding; missing-citation output is rejected.
- [ ] **9.2 Hallucination guardrails.** Grounding verification, confidence scoring, "unsure" state, and ensemble reconciliation with the rule/semantic layers. *Test:* measured hallucination rate at/near zero on the eval set.
- [ ] **9.3 Tiered routing + caching.** Deterministic path for the easy 80%; LLM only when needed. Prompt-cache the statute corpus; per-tenant token budgets. *Test:* routing sends easy clauses to rules, hard ones to LLM; budget enforced.
- [ ] **9.4 Feedback loop.** Reviewer approve/reject (already exists) becomes signal that reweights retrieval and few-shot examples. *Test:* rejected finding type is down-weighted on the next run.

**Exit:** the LLM path improves recall on novel clauses, every claim is cited, hallucination rate is near zero, and cost scales sub-linearly via routing + caching.

---

## Phase 10 — Clause Library & Precedent Search

**Horizon:** ~4–5 weeks · **Theme:** the org gets smarter over time.

Semantic search across all of an organization's past contracts — "find every indemnity clause we've agreed to" — building a reusable knowledge base. Pure reuse of the Phase 6 layer.

### Tasks

- [ ] **10.1 Precedent index.** Approved/library clauses embedded into an org-scoped precedent collection (extends the existing `clause_library_entries`). *Test:* approving a clause makes it retrievable in precedent search.
- [ ] **10.2 Precedent search API + UI.** Semantic search over the org's clause history, filterable by clause type; results link to source contracts. *Test:* a semantic query surfaces relevant historical clauses across projects.
- [ ] **10.3 "Compare to our standard" in findings.** When a clause deviates, show the org's own closest precedent alongside the template — "here's how we usually word this". *Test:* a deviating clause shows the nearest precedent.

**Exit:** an organization can semantically search its entire contract history and see its own precedents inline during review.

---

## Phase 11 — Agentic Orchestration (LangGraph)

**Horizon:** ~5–7 weeks · **Theme:** modern agentic architecture.

Restructure the four agents + the new retrieval/reasoning/verification steps into an explicit **LangGraph state machine** — inspectable, resumable, and the architecture that reads as genuinely current in an interview.

### Tasks

- [ ] **11.1 Define the graph.** Nodes: `ingest → retrieve → rule_check → semantic_check → llm_reason → guardrail/verify → reconcile → persist`. Edges encode the tiered routing from Phase 9. *Test:* the graph runs end-to-end on a sample project and produces the same findings as the current pipeline (parity test).
- [ ] **11.2 State + resumability.** Analysis state is checkpointed per node so a failed run resumes rather than restarts (ties into Part I Phase 4 reliability). *Test:* killing a run mid-graph and resuming produces a complete result.
- [ ] **11.3 Trace/inspection.** Persist each node's inputs/outputs for an "analysis trace" view (transparency + debugging). *Test:* the trace for a finding shows which node produced it and why.
- [ ] **11.4 Migrate agents into nodes.** Wrap the existing `TemplateComparison`, `VendorDiff`, `LawValidator`, `ChecklistValidator` as graph nodes with no behavioural change first, then enhance. *Test:* parity maintained after migration.

**Exit:** the whole analysis runs as an inspectable, resumable LangGraph; findings match or beat the pre-migration pipeline; each finding is traceable to the node that produced it.

---

## Cross-cutting: the "wow" layer (fold into the phases above)

These make it demo-outstanding; each rides on the retrieval/LLM layer already being built:

- **Contract risk score + analytics dashboard** — a 0–100 risk score per contract and a portfolio view (risk trends, most common issues across all contracts). *(Builds on Phase 7 confidence + Phase 9 reasoning.)*
- **Auto-redline export** — generate a `.docx` with the AI's accepted fixes applied as tracked changes, downloadable. *(Builds on the existing suggestion engine + Verify renderer.)*
- **Analysis trace / explainability view** — surface the LangGraph trace (Phase 11.3) so a reviewer sees exactly how a finding was reached. *(A trust + portfolio differentiator.)*

---

## Part II sequencing

```
Phase 6 (semantic foundation)  ← keystone; everything depends on it
   ├─→ Phase 7 (semantic analysis)
   ├─→ Phase 8 (RAG chatbot: project → org)      ← the standout demo feature
   └─→ Phase 10 (precedent search)
Phase 9 (LLM reasoning + guardrails)  ← ships WITH any LLM use, incl. the bot
Phase 11 (LangGraph orchestration)    ← once the nodes (rules/semantic/LLM) all exist
```

**Recommended first sprint of Part II:** Phase 6.1–6.6 (the pluggable semantic foundation, local provider) + Phase 8.1–8.4 (project-scoped RAG bot). That single sprint produces the headline demo — *"ask questions about your contract and get cited answers"* — running fully offline, and lays the layer every other phase reuses.

---

*This is a living document. Revise per phase completion — update the baseline section as gaps close, and record actual vs. estimated horizons for future planning accuracy.*
