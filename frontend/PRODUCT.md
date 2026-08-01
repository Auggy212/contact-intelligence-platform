# PRODUCT.md — ContractIQ

## What it is
ContractIQ is a multi-tenant SaaS platform for **AI-assisted legal contract review**,
built for legal teams (initially an Indian legal team in Mumbai). It compares three
versions of a contract — a company **Template (A)**, a **Proposed Draft (B)**, and a
**Vendor Reply (C)** — and surfaces every risk, deviation, and required fix.

## Register
**Product** (design serves the product). This is an authenticated dashboard / tool
where the user is in a focused review task. The interface should disappear into the
work, not call attention to itself.

## Who uses it & where
Lawyers, legal reviewers, and contract managers. Long focused sessions at a desk,
office lighting, reviewing dense legal text and structured findings. They need
**clarity, trust, scannability, and speed** — not decoration. The emotional register
is *calm, precise, authoritative* — the feeling of a well-organised legal desk, not a
consumer app.

## Core surfaces (in priority order)
1. **Findings** — the analysis output: a table of flagged clauses + a detail panel with
   clause text, severity, confidence, law citations, and suggested fixes. The "money" screen.
2. **Modifications (Fixes)** — every suggested correction grouped by priority; the
   actionable "here's what to change" report.
3. **Verify** — the original document rendered untouched with the matching clause
   highlighted when a finding is clicked. The trust-verification screen.
4. **Analysis** — run/monitor the 4 analysis agents.
5. **Dashboard / Projects** — overview and project management; first impression.
6. Supporting: Clause Library, Checklist Rules, Team, Audit Log, Billing, Settings.

## Design priorities
- **Trust and legibility first.** A lawyer who sees one sloppy element stops trusting
  the whole tool. Precision in spacing, alignment, and type is a feature.
- **Severity legibility.** Critical / High / Medium / Low / Info must be instantly
  distinguishable and consistent everywhere (badges, dots, table rows).
- **Density where it helps.** Findings tables and clause text can run dense; don't
  pad legal content into consumer-app airiness.
- **Restrained color.** Neutral canvas + one authoritative accent for actions/selection
  + a disciplined semantic severity scale. Color carries meaning, never decoration.
- **Deterministic, auditable feel.** The product's core value is that it's rule-based
  and explainable; the UI should feel exact and evidence-backed, not magical.

## Brand
- Name: **ContractIQ** · tagline "AI Legal Review".
- Existing identity: dark slate navigation shell, blue accent, Geist Sans.
  Preserve the identity direction (professional legal-tech) while elevating the craft.

## Non-goals
- Not a marketing site. No hero-metric templates, no drenched color, no display-font flourishes.
- Not a consumer app. Density and information clarity beat whitespace-for-elegance.
