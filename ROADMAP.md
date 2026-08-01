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

*This is a living document. Revise per phase completion — update the baseline section as gaps close, and record actual vs. estimated horizons for future planning accuracy.*
