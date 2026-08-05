# Semantic + RAG + Agentic — Technical Design Spec

> **Status:** Design approved (brainstorming phase, superpowers methodology). No code until Phase 6 tasks begin.
> **Date:** 2026-07-15
> **Covers:** chunking, embeddings, RAG tooling, vector store, database changes, the pluggable provider strategy, and the AWS deployment path.
> **Companion:** the phased task breakdown lives in `ROADMAP.md` → *Part II — Detailed AI Build Plan* (Phases 6–11).

---

## 0. The one idea everything hangs on

**Every AI operation runs behind a provider interface, so *where* it executes (local vs. a hosted API vs. AWS) is configuration, never a code change.** This is what makes the project both a laptop-runnable portfolio piece and an AWS-deployable industry product without a rewrite.

Three interfaces: `EmbeddingProvider`, `LlmProvider`, `OcrProvider`. Plus a `VectorStore` interface. All selected by env vars.

---

## 1. Locked-in decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Embeddings default** | **Local-first** — `BAAI/bge-small-en-v1.5` (384-dim) via `sentence-transformers` | Lightweight, runs fine on a laptop, free, offline. |
| **Embeddings API switch** | Voyage `voyage-law-2` (legal-tuned, already a dep) / OpenAI `text-embedding-3` | Best quality when a key is set. |
| **LLM default** | **Free hosted API** — Groq (primary) or Google Gemini (alt) | A local LLM needs heavy hardware; a free-tier API gives frontier-ish quality, zero cost, zero local load. Groq is extremely fast → the RAG bot feels instant. |
| **LLM production switch** | Claude API → later **Claude via AWS Bedrock** | Same model, same code, different endpoint when moving to AWS. |
| **RAG framework** | **Direct SDKs** for retrieval+generation; **LangGraph** for agentic orchestration (Phase 11). **Minimal/no LangChain.** | Keep control of the "grounded or nothing" guardrail; LangGraph only where statefulness earns its complexity. |
| **Vector store** | **Qdrant** primary (already provisioned); **pgvector** fallback behind the same interface | Qdrant gives payload filtering (tenant scoping), per-tenant collections, native hybrid search. Both already in the stack. |
| **Source of truth** | **Postgres**; Qdrant is a rebuildable derived index | If the vector index is lost, re-embed from Postgres — no data loss. |
| **Tenant isolation** | Existing Org→Project→Docs + Postgres RLS, **double-guarded** with Qdrant payload filters | RLS on metadata read AND scope filter on vector query — neither trusted alone. |

**Config surface (env vars):**
```
EMBEDDING_PROVIDER = local | voyage | openai        (default: local)
LLM_PROVIDER       = groq | gemini | anthropic | bedrock   (default: groq)
VECTOR_STORE       = qdrant | pgvector              (default: qdrant)
# keys only needed for the chosen providers:
GROQ_API_KEY / GEMINI_API_KEY / VOYAGE_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY
```
Each capability switches **independently** — e.g. local embeddings + Groq LLM is the default combo; nothing forces a single global mode.

---

## 2. Chunking

**Clause-aware hierarchical chunking** (not blind fixed-size). The parser already produces `ParsedClause` boundaries — that IS the chunking primitive.

- **Primary:** 1 chunk = 1 clause (`heading + body_text`).
- **Split:** clauses over the model token budget (~512) split on sentence boundaries with ~15% overlap.
- **Merge:** tiny fragments merge with a neighbor.
- **Metadata per chunk:** `chunk_id, clause_id, document_id, project_id, organization_id, file_role, clause_type, char_start, char_end`. The `char_start/end` powers citation deep-links into the Verify view.
- **Tooling:** small custom chunker (`app/ai/chunking.py`) + `tiktoken`/model tokenizer. No LangChain splitter needed.

## 3. Embeddings

- **Dense bi-encoder** vectors (one per chunk, cosine). Embed once at ingest, cache by `content_hash`, batch the calls in a Celery task.
- **Dimension is fixed per collection** — switching embedding providers requires a re-embed (documented migration step), because you can't mix dims in one index.
- Add a **sparse (BM25)** signal too → fused with dense (see retrieval), because legal text has exact terms (section numbers, dates, "MSME") where keywords still win.

## 4. RAG pipeline

- **Bot (Phase 8):** own thin orchestration — `retrieve(scope) → assemble grounded prompt → LlmProvider.complete() → parse + verify citations`. ~1 service file. Keeps the guardrail fully controlled.
- **Retrieval:** hybrid (BM25 + vector), reciprocal-rank-fused, **mandatory scope filter** (`project_id` or `organization_id`).
- **Agentic analysis (Phase 11):** LangGraph state machine — `ingest → retrieve → rule_check → semantic_check → llm_reason → guardrail/verify → reconcile → persist`, checkpointed for resumability.

---

## 5. Database changes

**New tables (Alembic migrations), all with `organization_id` + RLS:**
```
chunk_embeddings  — chunk_id, clause_id, document_id, project_id, organization_id,
                    vector_ref (Qdrant point id), content_hash, token_count, char_start/end
conversations     — id, scope ('project'|'org'), scope_id, organization_id, created_by
chat_messages     — conversation_id, role, content, citations (JSONB), created_at
```
Precedent search reuses existing `clause_library_entries` + its own embeddings.

**Pipeline gains a stage:** `upload → parse → clauses → [chunk → embed → index]` — the bracketed part is a new Celery task on a new `embed` queue (doesn't block parsing).

**pgvector option:** one config path stores vectors in a Postgres `vector` column instead of Qdrant — same `VectorStore` interface, for a "zero extra services" deployment.

---

## 6. AWS deployment ladder (LATER — only on company go-ahead)

Deferred until the app works and is approved. Documented so nothing built now blocks it.

- **Rung 1 — single box:** EC2 running the Docker stack (or RDS Postgres + ElastiCache Redis + EC2 app); documents → **S3** (MinIO is already S3-compatible → endpoint change only); AI → hosted APIs or Bedrock. *Pilot with 1–2 companies.*
- **Rung 2 — managed & separated (production):** ECS Fargate / EKS for API + workers (independent autoscale); **RDS Postgres** multi-AZ (pgvector image runs on RDS); **Qdrant Cloud** or self-hosted (compose already has the "swap for Qdrant Cloud" seam); **S3** + **Secrets Manager** + **Bedrock**.
- **Rung 3 — multi-tenant isolation model:** shared-DB + RLS (current, cheapest, scales) → optional silo (dedicated DB/collection/VPC) per enterprise client → Qdrant per-tenant collections map to isolated indexes per org.
- **AWS-native shortcut noted, not chosen:** Bedrock Knowledge Bases can do the whole RAG pipeline managed — but we build our own for portability + legal-grade guardrail control; keep Bedrock KB as a "could", not the default.

**Three commitments that keep the AWS move painless:**
1. Config-driven providers (env vars above) — local / Voyage / OpenAI / Groq / Gemini / Bedrock all selectable, no code change.
2. S3-compatible storage from day one (already true via MinIO).
3. No hard dependency on any single provider; Postgres = source of truth; keys from env/Secrets Manager, never hardcoded.

---

## 7. Honest tradeoffs to remember

- Local embeddings download a model (~130MB) + use some RAM — fine on a laptop, heavier than the pure-regex engine. Acceptable because embeddings are light; the LLM (the heavy part) is offloaded to a free API.
- Switching embedding providers = a re-embed (dimension change). Plan it as a migration, not a hot swap.
- Free LLM API tiers have rate limits; the provider interface means flipping Groq→Gemini→Claude is one env var if limits pinch.

---

*Design approved. Next step per superpowers: begin Phase 6 tasks (writing-plans) — provider interfaces + local embedding + chunking + vector store — TDD, no code until the go-ahead to implement.*
