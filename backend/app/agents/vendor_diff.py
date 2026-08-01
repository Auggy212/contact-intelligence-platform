"""
Agent 2: Vendor Diff Analyser

Analyses vendor reply (C) against proposed draft (B).

Analysis pipeline (all offline, no API keys):
  1. Noise filtering     — metadata, GSTIN, cover text excluded
  2. Clause classification — ClauseType assigned to every clause
  3. Heading-anchored clause alignment with body-text similarity fallback
  4. Value-level diff    — numeric/monetary/temporal extraction + comparison
     (runs even when text similarity is high — never silently ignores changes)
  5. OOXML tracked-change enrichment (insertions, deletions, strikethroughs)
  6. Line-level diff + risk-pattern scoring
  7. Removed-clause detection
  8. Dynamic confidence scoring
"""

from __future__ import annotations

import difflib
import re
from typing import Any

from app.agents.base_agent import PROMPT_VERSION, BaseAgent
from app.agents.clause_analyzer import (
    ClauseClassifier,
    ClauseType,
    ConfidenceScorer,
    ValueDiffEngine,
    build_value_change_evidence,
)
from app.agents import suggestion_builder as sb
from app.core.constants import FindingSeverity
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# NOISE FILTER
# ─────────────────────────────────────────────────────────────────────────────

_NOISE_RE = [
    re.compile(r"^(?:file\s+role|upload\s+as|upload\s+this|vendor\s+proposed|company\s+master|gold\s+standard)", re.I),
    re.compile(r"^(?:CIN|GSTIN|U\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})", re.I),
    re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}\d[Z][A-Z\d]$"),
    re.compile(r"^\s*(?:DEVIATION|deviation|NOTE|note|EDGE\s+CASE)\s*[:—]", re.I),
    re.compile(r"^\[(?:DEVIATION|NOTE|CRITICAL|EDGE\s+CASE)", re.I),
    re.compile(r"^(?:⚡|📝|⚠)\s*"),
    re.compile(r"^(?:track\s+changes|red\s+=\s+deleted|green\s+=\s+inserted)", re.I),
]


def _is_noise(clause: dict) -> bool:
    text    = (clause.get("body_text") or "").strip()
    heading = (clause.get("heading")   or "").strip()
    if len(text) < 15:
        return True
    for p in _NOISE_RE:
        if p.search(text) or p.search(heading):
            return True
    if re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]$", text.strip()):
        return True
    if re.match(r"^[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$", text.strip()):
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# RISK PATTERN LISTS
# ─────────────────────────────────────────────────────────────────────────────

_HIGH_RISK_ADD_PATTERNS = [
    (r"\bno\s+liabilit\w*",                         "Liability exclusion added"),
    (r"\bwaive[sd]?\b.{0,30}\bright\b",             "Rights waiver added"),
    (r"\bexclusive\b.{0,20}\bjurisdiction\b",       "Exclusive jurisdiction clause added"),
    (r"\bindemnif\w*",                               "Indemnification clause modified"),
    (r"\bunlimited\b.{0,20}\bliabilit\w*",          "Unlimited liability clause added"),
    (r"\bnon[- ]?compet\w*",                        "Non-compete clause added"),
    (r"\bintellectual\s+property\b.{0,30}\bassign\w*", "IP assignment clause added"),
    (r"\bperpetu\w*",                               "Perpetual obligation added"),
    (r"\birrevocabl\w*",                            "Irrevocable clause added"),
    (r"\bno\s+refund\b|\bnon[- ]?refundable\b",    "No-refund clause added"),
    (r"\bunilateral\b.{0,30}\bterminat\w*",         "Unilateral termination right added"),
    (r"\bsole\s+discretion\b",                      "Sole discretion clause added"),
    (r"\bwithout\s+cause\b",                        "Termination without cause added"),
    (r"\bautomatic\s+renewal\b|\bauto[- ]?renew\b", "Auto-renewal clause added"),
    (r"\bpenalt\w*\s+of\s+\d+\s*%",                "Penalty rate added"),
    (r"\bliquidated\s+damages\b",                   "Liquidated damages clause added"),
    (r"\bnon[- ]?solicit\w*\b",                     "Non-solicitation clause added"),
    (r"\bclass\s+action\b",                         "Class action waiver added"),
    (r"\bexclusiv\w+\s+provider\b",                 "Exclusivity obligation added"),
]

_HIGH_RISK_REMOVE_PATTERNS = [
    (r"\bgoverning\s+law\b",                        "Governing law clause removed"),
    (r"\bdispute\s+resolution\b|\barbitrat\w*",     "Dispute resolution removed"),
    (r"\bwarrant\w*",                               "Warranty removed"),
    (r"\bconfidential\w*",                          "Confidentiality obligation removed"),
    (r"\bpayment\s+terms?\b",                       "Payment terms removed"),
    (r"\bterminat\w*",                              "Termination clause removed"),
    (r"\bforce\s+majeure\b",                        "Force majeure clause removed"),
    (r"\bnotice\s+period\b|\bprior\s+notice\b",    "Notice period removed"),
    (r"\bindemnif\w*",                              "Indemnification protection removed"),
    (r"\blimit(?:ation)?\s+of\s+liabilit\w*",      "Liability cap removed"),
    (r"\baudit\b",                                  "Audit rights removed"),
    (r"\bdata\s+protection\b|\bdpdp\b",             "Data protection clause removed"),
]


def _check_patterns(text: str, patterns: list[tuple]) -> list[str]:
    return [lbl for pat, lbl in patterns if re.search(pat, text, re.I)]


# ─────────────────────────────────────────────────────────────────────────────
# TEXT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_heading(h: str) -> str:
    h = re.sub(r"^[\d\.]+\s*", "", (h or "")).strip().lower()
    return re.sub(r"\s+", " ", h)


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(
        None,
        re.sub(r"\s+", " ", a.lower()),
        re.sub(r"\s+", " ", b.lower()),
    ).ratio()


def _diff_lines(b: str, c: str) -> tuple[list[str], list[str]]:
    lb = b.splitlines() if b else []
    lc = c.splitlines() if c else []
    diff = list(difflib.unified_diff(lb, lc, lineterm="", n=0))
    added   = [l[1:].strip() for l in diff if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:].strip() for l in diff if l.startswith("-") and not l.startswith("---")]
    return [a for a in added if a], [r for r in removed if r]


def _score_change(
    added: list[str], removed: list[str], has_ooxml: bool
) -> tuple[int, str, FindingSeverity]:
    added_txt   = " ".join(added)
    removed_txt = " ".join(removed)
    hits_add = _check_patterns(added_txt,   _HIGH_RISK_ADD_PATTERNS)
    hits_rem = _check_patterns(removed_txt, _HIGH_RISK_REMOVE_PATTERNS)
    total_risks = len(hits_add) + len(hits_rem)
    base   = min(3 + (len(added) + len(removed)) // 2, 6)
    score  = min(10, base + min(total_risks * 2, 4) + (1 if has_ooxml else 0))
    parts  = []
    if added:
        parts.append(f"{len(added)} line(s) added")
    if removed:
        parts.append(f"{len(removed)} line(s) removed")
    summary = ", ".join(parts) or "Minor formatting change"
    if hits_add + hits_rem:
        summary += f". Risk: {'; '.join(hits_add + hits_rem)}"
    sev = (FindingSeverity.CRITICAL if score >= 8 else
           FindingSeverity.HIGH     if score >= 6 else
           FindingSeverity.MEDIUM   if score >= 4 else
           FindingSeverity.LOW)
    return score, summary, sev


def _ooxml_context(clause: dict) -> str:
    parts = []
    meta = clause.get("change_metadata", {})
    if clause.get("has_tracked_insertion") and meta.get("insertions"):
        parts.append(f"Vendor inserted: {meta['insertions'][:3]}")
    if clause.get("has_tracked_deletion") and meta.get("deletions"):
        parts.append(f"Vendor deleted: {meta['deletions'][:3]}")
    if clause.get("has_strikethrough"):
        parts.append("Strikethrough text present")
    return "; ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# CLAUSE ALIGNMENT
# ─────────────────────────────────────────────────────────────────────────────

def _build_b_index(clauses_b: list[dict]) -> tuple[dict[str, dict], dict[int, dict]]:
    by_heading: dict[str, dict] = {}
    by_idx:     dict[int, dict] = {}
    for cb in clauses_b:
        h = _normalize_heading(cb.get("heading") or "")
        if h and h not in by_heading:
            by_heading[h] = cb
        by_idx[cb.get("paragraph_index", -1)] = cb
    return by_heading, by_idx


def _find_best_b(
    clause_c: dict,
    by_heading: dict[str, dict],
    by_idx: dict[int, dict],
    clauses_b: list[dict],
) -> tuple[dict | None, bool]:
    """Return (best_b_clause, heading_matched)."""
    hc = _normalize_heading(clause_c.get("heading") or "")
    tc = (clause_c.get("body_text") or "").strip()

    if hc and hc in by_heading:
        return by_heading[hc], True

    best_h_match = None
    best_h_score = 0.0
    for h, cb in by_heading.items():
        s = difflib.SequenceMatcher(None, hc, h).ratio()
        if s > best_h_score:
            best_h_score, best_h_match = s, cb
    if best_h_score >= 0.80 and best_h_match is not None:
        return best_h_match, True

    if tc:
        best_body = None
        best_bs   = 0.0
        for cb in clauses_b:
            s = _similarity(cb.get("body_text", ""), tc)
            if s > best_bs:
                best_bs, best_body = s, cb
        if best_bs > 0.30 and best_body is not None:
            return best_body, False

    return by_idx.get(clause_c.get("paragraph_index", -1)), False


# ─────────────────────────────────────────────────────────────────────────────
# AGENT
# ─────────────────────────────────────────────────────────────────────────────

class VendorDiffAgent(BaseAgent):
    name = "vendor_diff"

    def __init__(self) -> None:
        super().__init__()
        self._diff_engine = ValueDiffEngine()

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        project_id = context["project_id"]
        tenant_id  = context["tenant_id"]
        clauses_b  = context.get("clauses_b", [])
        clauses_c  = context.get("clauses_c", [])

        self._log_run_start(project_id, tenant_id)

        # Classify all clauses
        clauses_b = ClauseClassifier.classify_all(clauses_b)
        clauses_c = ClauseClassifier.classify_all(clauses_c)

        findings: list[dict] = []
        by_heading, by_idx = _build_b_index(clauses_b)
        seen_b_ids: set[str] = set()

        # ── Scan C clauses against B ──────────────────────────────────────
        for cc in clauses_c:
            tc = (cc.get("body_text") or "").strip()
            if not tc or _is_noise(cc):
                continue

            ctype_str = cc.get("clause_type", ClauseType.MISCELLANEOUS.value)
            try:
                ctype = ClauseType(ctype_str)
            except ValueError:
                ctype = ClauseType.MISCELLANEOUS

            has_ooxml = bool(
                cc.get("has_tracked_insertion") or
                cc.get("has_tracked_deletion") or
                cc.get("has_strikethrough")
            )

            clause_b_match, heading_matched = _find_best_b(cc, by_heading, by_idx, clauses_b)
            tb = (clause_b_match.get("body_text") or "").strip() if clause_b_match else ""

            if clause_b_match:
                seen_b_ids.add(str(clause_b_match.get("id", "")))

            sim = _similarity(tb, tc) if tb else 0.0

            if sim > 0.95 and not has_ooxml:
                continue  # virtually identical, no tracked changes

            added, removed = _diff_lines(tb, tc)
            if not added and not removed and not has_ooxml:
                continue

            # ── Value-level diff (runs even on high-sim clauses) ───────────
            if clause_b_match:
                value_changes = self._diff_engine.diff(clause_b_match, cc, ctype)
            else:
                value_changes = []

            for vc in value_changes:
                vc_conf = ConfidenceScorer.score(
                    text_similarity=sim,
                    heading_matched=heading_matched,
                    has_ooxml_changes=has_ooxml,
                    value_changes_count=1,
                    clause_type_known=(ctype != ClauseType.MISCELLANEOUS),
                )
                findings.append(self._build_finding(
                    flag_type="vendor_redline",
                    severity=vc.severity,
                    title=f"[Value Change] {vc.label}: {vc.old_display} → {vc.new_display}",
                    description=(
                        f"[Clause Type: {vc.clause_type}] "
                        f"{vc.explanation} "
                        f"Text similarity B→C: {sim:.0%}."
                    ),
                    recommendation=f"Review this change. {vc.explanation}",
                    source_clause_id=str(cc.get("id", "")),
                    confidence=vc_conf,
                    reasoning_trace=(
                        f"clause_type={vc.clause_type}; field={vc.field}; "
                        f"old={vc.old_value}; new={vc.new_value}; "
                        f"change_pct={vc.change_pct}%; "
                        f"text_sim={sim:.3f}; ooxml={has_ooxml}"
                    ),
                    risk_score=vc.risk_score,
                    clause_type=vc.clause_type,
                    value_changes=[{
                        "field": vc.field,
                        "label": vc.label,
                        "old_value": vc.old_value,
                        "new_value": vc.new_value,
                        "old_display": vc.old_display,
                        "new_display": vc.new_display,
                        "change_pct": vc.change_pct,
                        "direction": vc.direction,
                        "severity": vc.severity,
                        "risk_score": vc.risk_score,
                        "change_category": vc.change_category,
                        "evidence": vc.evidence,
                        "explanation": vc.explanation,
                    }],
                    suggestion=sb.for_value_change(vc, basis="vendor_draft").as_dict(),
                    priority=sb.priority_for(vc.severity),
                ))

            # ── Line-level diff + risk pattern finding ─────────────────────
            risk_score, summary, severity = _score_change(added, removed, has_ooxml)

            ooxml_ctx = _ooxml_context(cc)
            evidence  = build_value_change_evidence(value_changes)

            if tb:
                base_desc = f"[Clause Type: {ctype_str}] Text similarity B→C: {sim:.0%}. {summary}."
            else:
                base_desc = f"[Clause Type: {ctype_str}] New clause in vendor reply (no equivalent in proposed draft). {summary}."

            if ooxml_ctx:
                base_desc += f" OOXML tracked changes: {ooxml_ctx}."
            if evidence:
                base_desc += f"\n{evidence}"

            conf = ConfidenceScorer.score(
                text_similarity=sim,
                heading_matched=heading_matched,
                has_ooxml_changes=has_ooxml,
                value_changes_count=len(value_changes),
                clause_type_known=(ctype != ClauseType.MISCELLANEOUS),
            )

            findings.append(self._build_finding(
                flag_type="vendor_redline",
                severity=severity,
                title=f"Vendor change: {cc.get('heading') or ctype_str or ('Clause ' + str(cc.get('paragraph_index', '?')))}",
                description=base_desc,
                recommendation=(
                    "Review the vendor's modifications carefully. "
                    "Ensure changes to liability, payment, termination, or IP clauses "
                    "are approved by legal counsel."
                ),
                source_clause_id=str(cc.get("id", "")),
                confidence=conf,
                reasoning_trace=(
                    f"clause_type={ctype_str}; similarity={sim:.3f}; "
                    f"added_lines={len(added)}; removed_lines={len(removed)}; "
                    f"ooxml={has_ooxml}; value_changes={len(value_changes)}; "
                    f"matched_b='{(clause_b_match or {}).get('heading')}'"
                ),
                risk_score=risk_score,
                clause_type=ctype_str,
                priority=sb.priority_for(severity),
            ))

        # ── Detect B clauses entirely removed by vendor in C ─────────────
        c_headings = {_normalize_heading(cc.get("heading") or "") for cc in clauses_c}
        for cb in clauses_b:
            if _is_noise(cb):
                continue
            tb = (cb.get("body_text") or "").strip()
            if not tb or len(tb) < 20:
                continue
            if str(cb.get("id", "")) in seen_b_ids:
                continue
            hb = _normalize_heading(cb.get("heading") or "")
            if hb and hb in c_headings:
                continue

            ctype_str = cb.get("clause_type", ClauseType.MISCELLANEOUS.value)
            risk_kws  = _check_patterns(tb, _HIGH_RISK_REMOVE_PATTERNS)
            sev       = FindingSeverity.HIGH if risk_kws else FindingSeverity.MEDIUM
            conf      = ConfidenceScorer.score(
                clause_type_known=(ctype_str != ClauseType.MISCELLANEOUS.value),
            )

            findings.append(self._build_finding(
                flag_type="vendor_redline",
                severity=sev,
                title=f"Clause removed by vendor: {cb.get('heading') or ctype_str or 'Untitled'}",
                description=(
                    f"[Clause Type: {ctype_str}] "
                    f"This clause from the proposed draft was entirely removed in the vendor reply."
                    + (f" Risk: {'; '.join(risk_kws)}." if risk_kws else "")
                ),
                recommendation=(
                    "Confirm whether this omission is acceptable. "
                    "Key clauses (governing law, dispute resolution, confidentiality) "
                    "must not be silently dropped."
                ),
                source_clause_id=str(cb.get("id", "")),
                confidence=conf,
                reasoning_trace=f"clause_type={ctype_str}; heading '{hb}' not found in vendor reply",
                risk_score=7 if risk_kws else 5,
                clause_type=ctype_str,
                suggestion=sb.for_missing_clause(
                    clause_heading=cb.get("heading"),
                    template_body=tb,
                    severity=sev,
                ).as_dict(),
                priority=sb.priority_for(sev),
            ))

        self._log_run_complete(project_id, len(findings))

        return {
            "findings": findings,
            "token_usage": {"input_tokens": 0, "output_tokens": 0},
            "model_version": "python-vendor-diff-v2-with-value-diff",
            "prompt_version": PROMPT_VERSION,
        }
