"""
Agent 2: Vendor Diff Analyser (demo mode — no API keys required)

Analyses vendor reply (C) against proposed draft (B). Uses:
  - Heading-based clause alignment (not fragile paragraph-index matching)
  - OOXML tracked change metadata (insertions, deletions, strikethroughs) when present
  - difflib text diff for untracked changes
  - Rule-based risk scoring on detected change patterns
"""

import difflib
import re
from typing import Any

from app.agents.base_agent import PROMPT_VERSION, BaseAgent
from app.core.constants import FindingSeverity
from app.core.logging import get_logger

logger = get_logger(__name__)

# Patterns that signal high legal risk when added by the vendor
_HIGH_RISK_ADD_PATTERNS = [
    (r"\bno\s+liabilit\w*", "Liability exclusion added"),
    (r"\bwaive[sd]?\b.{0,30}\bright\b", "Rights waiver added"),
    (r"\bexclusive\b.{0,20}\bjurisdiction\b", "Exclusive jurisdiction clause added"),
    (r"\bindemnif\w*", "Indemnification clause modified"),
    (r"\bunlimited\b.{0,20}\bliabilit\w*", "Unlimited liability clause added"),
    (r"\bnon[- ]?compet\w*", "Non-compete clause added"),
    (r"\bintellectual\s+property\b.{0,30}\bassign\w*", "IP assignment clause added"),
    (r"\bperpetu\w*", "Perpetual obligation added"),
    (r"\birrevocabl\w*", "Irrevocable clause added"),
    (r"\bno\s+refund\b|\bnon[- ]?refundable\b", "No-refund clause added"),
    (r"\bunilateral\b.{0,30}\bterminat\w*", "Unilateral termination right added"),
    (r"\bsole\s+discretion\b", "Sole discretion clause added"),
    (r"\bwithout\s+cause\b", "Termination without cause added"),
    (r"\bautomatic\s+renewal\b|\bauto[- ]?renew\b", "Auto-renewal clause added"),
]

# Patterns that signal high legal risk when removed by the vendor
_HIGH_RISK_REMOVE_PATTERNS = [
    (r"\bgoverning\s+law\b", "Governing law clause removed"),
    (r"\bdispute\s+resolution\b|\barbitrat\w*", "Dispute resolution clause removed"),
    (r"\bwarrant\w*", "Warranty clause removed"),
    (r"\bconfidential\w*", "Confidentiality obligation removed"),
    (r"\bpayment\s+terms?\b", "Payment terms removed"),
    (r"\bterminat\w*", "Termination clause removed"),
    (r"\bforce\s+majeure\b", "Force majeure clause removed"),
    (r"\bnotice\s+period\b|\bprior\s+notice\b", "Notice period removed"),
    (r"\bindemnif\w*", "Indemnification protection removed"),
    (r"\blimit(ation)?\s+of\s+liabilit\w*", "Liability cap removed"),
]


def _normalize_heading(heading: str) -> str:
    h = re.sub(r"^[\d\.]+\s*", "", (heading or "")).strip().lower()
    return re.sub(r"\s+", " ", h)


def _check_patterns(text: str, patterns: list[tuple]) -> list[str]:
    hits = []
    for pattern, label in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(label)
    return hits


def _similarity(text_a: str, text_b: str) -> float:
    if not text_a or not text_b:
        return 0.0
    norm_a = re.sub(r"\s+", " ", text_a.lower())
    norm_b = re.sub(r"\s+", " ", text_b.lower())
    return difflib.SequenceMatcher(None, norm_a, norm_b).ratio()


def _diff_lines(text_b: str, text_c: str) -> tuple[list[str], list[str]]:
    """Return (added_lines, removed_lines) comparing B→C."""
    lines_b = text_b.splitlines() if text_b else []
    lines_c = text_c.splitlines() if text_c else []
    diff = list(difflib.unified_diff(lines_b, lines_c, lineterm="", n=0))
    added = [l[1:].strip() for l in diff if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:].strip() for l in diff if l.startswith("-") and not l.startswith("---")]
    return [a for a in added if a], [r for r in removed if r]


def _score_change(
    added: list[str], removed: list[str], has_ooxml_changes: bool
) -> tuple[int, str, FindingSeverity]:
    """Compute risk score 1-10, summary string, and severity."""
    added_text = " ".join(added)
    removed_text = " ".join(removed)

    risk_hits_add = _check_patterns(added_text, _HIGH_RISK_ADD_PATTERNS)
    risk_hits_rem = _check_patterns(removed_text, _HIGH_RISK_REMOVE_PATTERNS)

    total_risks = len(risk_hits_add) + len(risk_hits_rem)
    total_lines_changed = len(added) + len(removed)

    base = min(3 + total_lines_changed // 2, 6)
    risk_bump = min(total_risks * 2, 4)
    ooxml_bump = 1 if has_ooxml_changes else 0
    score = min(10, base + risk_bump + ooxml_bump)

    concerns = risk_hits_add + risk_hits_rem
    summary_parts = []
    if added:
        summary_parts.append(f"{len(added)} line(s) added")
    if removed:
        summary_parts.append(f"{len(removed)} line(s) removed")
    summary = ", ".join(summary_parts) or "Minor formatting change"
    if concerns:
        summary += f". Risk flags: {'; '.join(concerns)}"

    if score >= 8:
        severity = FindingSeverity.CRITICAL
    elif score >= 6:
        severity = FindingSeverity.HIGH
    elif score >= 4:
        severity = FindingSeverity.MEDIUM
    else:
        severity = FindingSeverity.LOW

    return score, summary, severity


def _format_redline_context(clause: dict) -> str:
    parts = []
    meta = clause.get("change_metadata", {})
    if clause.get("has_tracked_insertion") and meta.get("insertions"):
        parts.append(f"Vendor inserted: {meta['insertions'][:3]}")
    if clause.get("has_tracked_deletion") and meta.get("deletions"):
        parts.append(f"Vendor deleted: {meta['deletions'][:3]}")
    if clause.get("has_strikethrough"):
        parts.append("Strikethrough formatting present")
    return "; ".join(parts)


def _build_b_index(clauses_b: list[dict]) -> tuple[dict, dict]:
    """
    Build two lookup maps for B clauses:
      - by normalized heading (primary, more robust)
      - by paragraph_index (fallback)
    """
    by_heading: dict[str, dict] = {}
    by_idx: dict[int, dict] = {}
    for cb in clauses_b:
        h = _normalize_heading(cb.get("heading") or "")
        if h and h not in by_heading:
            by_heading[h] = cb
        by_idx[cb.get("paragraph_index", -1)] = cb
    return by_heading, by_idx


def _find_best_b_match(clause_c: dict, by_heading: dict, by_idx: dict, clauses_b: list[dict]) -> dict | None:
    """
    Find the matching B clause for a given C clause.
    Priority: exact heading match → best body similarity → paragraph index.
    """
    heading_c = _normalize_heading(clause_c.get("heading") or "")
    text_c = (clause_c.get("body_text") or "").strip()

    # 1. Exact heading match
    if heading_c and heading_c in by_heading:
        return by_heading[heading_c]

    # 2. Close heading match (>=80% similarity)
    best_head_match = None
    best_head_score = 0.0
    for h, cb in by_heading.items():
        score = difflib.SequenceMatcher(None, heading_c, h).ratio()
        if score > best_head_score:
            best_head_score = score
            best_head_match = cb
    if best_head_score >= 0.80 and best_head_match is not None:
        return best_head_match

    # 3. Best body text similarity
    if text_c:
        best_body_match = None
        best_body_score = 0.0
        for cb in clauses_b:
            score = _similarity(cb.get("body_text", ""), text_c)
            if score > best_body_score:
                best_body_score = score
                best_body_match = cb
        if best_body_score > 0.30 and best_body_match is not None:
            return best_body_match

    # 4. Paragraph index fallback
    return by_idx.get(clause_c.get("paragraph_index", -1))


class VendorDiffAgent(BaseAgent):
    name = "vendor_diff"

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        project_id = context["project_id"]
        tenant_id = context["tenant_id"]
        clauses_b = context.get("clauses_b", [])
        clauses_c = context.get("clauses_c", [])

        self._log_run_start(project_id, tenant_id)
        findings = []

        by_heading, by_idx = _build_b_index(clauses_b)

        seen_b_ids: set[str] = set()

        for clause_c in clauses_c:
            text_c = (clause_c.get("body_text") or "").strip()
            if not text_c:
                continue

            has_ooxml = bool(
                clause_c.get("has_tracked_insertion")
                or clause_c.get("has_tracked_deletion")
                or clause_c.get("has_strikethrough")
            )

            clause_b = _find_best_b_match(clause_c, by_heading, by_idx, clauses_b)
            text_b = (clause_b.get("body_text") or "").strip() if clause_b else ""

            if clause_b:
                seen_b_ids.add(str(clause_b.get("id", "")))

            sim = _similarity(text_b, text_c) if text_b else 0.0

            # Skip virtually identical clauses with no OOXML changes
            if sim > 0.95 and not has_ooxml:
                continue

            added, removed = _diff_lines(text_b, text_c)

            # Skip if truly no diff and no tracked changes
            if not added and not removed and not has_ooxml:
                continue

            risk_score, summary, severity = _score_change(added, removed, has_ooxml)

            ooxml_context = _format_redline_context(clause_c)
            description = f"Text similarity B→C: {sim:.0%}. {summary}."
            if ooxml_context:
                description += f" OOXML tracked changes: {ooxml_context}."
            if not text_b:
                description = f"New clause in vendor reply (not present in proposed draft). {summary}."

            confidence = 0.88 if has_ooxml else 0.75

            findings.append(self._build_finding(
                flag_type="vendor_redline",
                severity=severity,
                title=f"Vendor change: {clause_c.get('heading') or 'Clause ' + str(clause_c.get('paragraph_index', '?'))}",
                description=description,
                recommendation=(
                    "Review the vendor's modifications carefully. "
                    "Ensure any changes to key terms (liability, payment, termination, IP) "
                    "are reviewed and approved by legal counsel."
                ),
                source_clause_id=str(clause_c.get("id", "")),
                confidence=confidence,
                reasoning_trace=(
                    f"similarity={sim:.3f}; added_lines={len(added)}; removed_lines={len(removed)}; "
                    f"ooxml_changes={has_ooxml}; matched_b='{(clause_b or {}).get('heading')}'"
                ),
                risk_score=risk_score,
            ))

        # Detect clauses in B that vendor completely removed in C
        b_headings_in_c = {
            _normalize_heading(cc.get("heading") or "") for cc in clauses_c
        }
        for cb in clauses_b:
            text_b = (cb.get("body_text") or "").strip()
            if not text_b or len(text_b) < 20:
                continue
            heading_b = _normalize_heading(cb.get("heading") or "")
            bid = str(cb.get("id", ""))
            if bid in seen_b_ids:
                continue
            if heading_b and heading_b in b_headings_in_c:
                continue
            # Vendor has dropped this clause entirely
            risk_kws = _check_patterns(text_b, _HIGH_RISK_REMOVE_PATTERNS)
            severity = FindingSeverity.HIGH if risk_kws else FindingSeverity.MEDIUM
            findings.append(self._build_finding(
                flag_type="vendor_redline",
                severity=severity,
                title=f"Clause removed by vendor: {cb.get('heading') or 'Untitled'}",
                description=(
                    f"This clause from the proposed draft was entirely removed in the vendor reply. "
                    + (f"Risk: {'; '.join(risk_kws)}." if risk_kws else "")
                ),
                recommendation=(
                    "Confirm whether this omission is acceptable. "
                    "Key clauses (governing law, dispute resolution, confidentiality) must not be silently dropped."
                ),
                source_clause_id=str(cb.get("id", "")),
                confidence=0.78,
                reasoning_trace=f"Heading '{heading_b}' not found in vendor reply; clause not matched",
                risk_score=7 if risk_kws else 5,
            ))

        self._log_run_complete(project_id, len(findings))

        return {
            "findings": findings,
            "token_usage": {"input_tokens": 0, "output_tokens": 0},
            "model_version": "python-heading-aligned-diff-demo",
            "prompt_version": PROMPT_VERSION,
        }
