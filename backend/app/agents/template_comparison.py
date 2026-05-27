"""
Agent 1: Template Comparison Agent (demo mode — no API keys required)

Compares master template (A) against proposed draft (B) using a combination of
difflib SequenceMatcher and n-gram Jaccard similarity for more robust clause matching.
Flags clauses in B that are missing, significantly altered, or added relative to A.
"""

import difflib
import re
from collections import Counter
from typing import Any

from app.agents.base_agent import PROMPT_VERSION, BaseAgent
from app.core.constants import FindingSeverity
from app.core.logging import get_logger

logger = get_logger(__name__)

# Similarity below this → clause is flagged as significantly altered
_ALTERED_THRESHOLD = 0.55
# Similarity below this → clause is flagged as critically different
_CRITICAL_THRESHOLD = 0.25

# High-risk keywords with their human-readable labels
_RISK_KEYWORD_MAP = [
    (r"\bindemnif\w*", "indemnification"),
    (r"\bliabilit\w*", "liability"),
    (r"\bwarrant\w*", "warranty"),
    (r"\bpenalt\w*", "penalty"),
    (r"\bterminate\b|\btermination\b", "termination"),
    (r"\bconfidential\w*", "confidentiality"),
    (r"\barbitrat\w*", "arbitration"),
    (r"\bexclusive\b", "exclusivity"),
    (r"\bnon[- ]?compet\w*", "non-compete"),
    (r"\bforce\s+majeure\b", "force majeure"),
    (r"\bintellectual\s+property\b|\bIP\s+rights?\b", "intellectual property"),
    (r"\bgoverning\s+law\b", "governing law"),
    (r"\bjurisdiction\b", "jurisdiction"),
    (r"\bno\s+liabilit\w*|\bliability.{0,15}excluded\b", "liability exclusion"),
    (r"\bno\s+refund\b|\bnon[- ]refundable\b", "no-refund clause"),
]


def _normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation for cleaner comparison."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _ngrams(text: str, n: int = 3) -> Counter:
    """Character n-gram frequency counter."""
    words = text.split()
    return Counter(" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1)))


def _jaccard(text_a: str, text_b: str, n: int = 3) -> float:
    """Jaccard similarity on word n-grams."""
    a = set(_ngrams(text_a, n).keys())
    b = set(_ngrams(text_b, n).keys())
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _token_overlap(text_a: str, text_b: str) -> float:
    """Fraction of words in B that also appear in A."""
    words_a = set(text_a.split())
    words_b = set(text_b.split())
    if not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_b)


def _composite_similarity(text_a: str, text_b: str) -> float:
    """
    Combine three signals for a more robust similarity score:
      40% SequenceMatcher (character-level)
      35% trigram Jaccard (phrase-level)
      25% token overlap (vocabulary-level)
    """
    norm_a = _normalize(text_a)
    norm_b = _normalize(text_b)
    if not norm_a or not norm_b:
        return 0.0
    seq = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
    jac = _jaccard(norm_a, norm_b, n=3)
    tok = _token_overlap(norm_a, norm_b)
    return 0.40 * seq + 0.35 * jac + 0.25 * tok


def _normalize_heading(heading: str) -> str:
    """Strip clause numbers and lowercase for heading comparison."""
    h = re.sub(r"^[\d\.]+\s*", "", heading or "").strip().lower()
    h = re.sub(r"\s+", " ", h)
    return h


def _best_match(
    clause_b: dict, clauses_a: list[dict]
) -> tuple[dict | None, float]:
    """
    Find the clause in A most similar to clause_b.
    Heading match gets a 0.15 bonus so same-titled clauses always align.
    Returns (clause_a, combined_score).
    """
    best_clause = None
    best_score = -1.0
    heading_b = _normalize_heading(clause_b.get("heading") or "")
    text_b = (clause_b.get("body_text") or "").strip()

    for ca in clauses_a:
        heading_a = _normalize_heading(ca.get("heading") or "")
        text_a = (ca.get("body_text") or "").strip()

        body_score = _composite_similarity(text_a, text_b)

        # Boost when headings match (exact or high similarity)
        if heading_a and heading_b:
            head_sim = difflib.SequenceMatcher(None, heading_a, heading_b).ratio()
            if head_sim >= 0.85:
                body_score = min(1.0, body_score + 0.15)

        if body_score > best_score:
            best_score = body_score
            best_clause = ca

    return best_clause, max(0.0, best_score)


def _diff_summary(text_a: str, text_b: str) -> str:
    """Produce a short human-readable diff summary."""
    lines_a = text_a.splitlines() or [text_a]
    lines_b = text_b.splitlines() or [text_b]
    diff = list(difflib.unified_diff(lines_a, lines_b, lineterm="", n=1))
    if not diff:
        return "No textual differences detected."
    added = [l[1:].strip() for l in diff if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:].strip() for l in diff if l.startswith("-") and not l.startswith("---")]
    parts = []
    if removed:
        parts.append(f"Removed: \"{'; '.join(removed[:2])}\"")
    if added:
        parts.append(f"Added: \"{'; '.join(added[:2])}\"")
    return "; ".join(parts) or "Minor whitespace/formatting changes."


def _risk_keywords(text: str) -> list[str]:
    """Detect high-risk legal keywords, return human-readable labels."""
    found = []
    for pattern, label in _RISK_KEYWORD_MAP:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(label)
    return found


def _count_word_changes(text_a: str, text_b: str) -> tuple[int, int]:
    """Count inserted and deleted words between two texts."""
    words_a = set(_normalize(text_a).split())
    words_b = set(_normalize(text_b).split())
    added = len(words_b - words_a)
    removed = len(words_a - words_b)
    return added, removed


class TemplateComparisonAgent(BaseAgent):
    name = "template_comparison"

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        project_id = context["project_id"]
        tenant_id = context["tenant_id"]
        clauses_a = context.get("clauses_a", [])
        clauses_b = context.get("clauses_b", [])

        self._log_run_start(project_id, tenant_id)

        findings = []

        # ── Step 1: detect clauses in B that are altered or new vs A ──────────
        matched_a_ids: set[str] = set()

        for clause_b in clauses_b:
            text_b = (clause_b.get("body_text") or "").strip()
            if not text_b or len(text_b) < 20:
                continue

            best_a, score = _best_match(clause_b, clauses_a)

            if best_a is None or score < 0.10:
                # No meaningful match — this clause is new in B
                risk_kws = _risk_keywords(text_b)
                severity = FindingSeverity.HIGH if risk_kws else FindingSeverity.MEDIUM
                findings.append(self._build_finding(
                    flag_type="clause_added",
                    severity=severity,
                    title=f"New clause in draft (not in template): {clause_b.get('heading') or 'Untitled'}",
                    description=(
                        f"This clause appears in the proposed draft but has no equivalent in the "
                        f"master template (best similarity: {score:.0%}). "
                        + (f"Contains risk keywords: {', '.join(risk_kws)}." if risk_kws else "")
                    ),
                    recommendation=(
                        "Review whether this clause should be included and whether it aligns "
                        "with company policy and standard templates."
                    ),
                    source_clause_id=str(clause_b.get("id", "")),
                    confidence=0.82,
                    reasoning_trace=f"No template clause matched above 10% similarity; best_score={score:.3f}",
                    risk_score=7 if risk_kws else 4,
                ))
                continue

            matched_a_ids.add(str(best_a.get("id", "")))

            if score >= _ALTERED_THRESHOLD:
                # Acceptable similarity — no finding
                continue

            # Significantly altered
            diff_note = _diff_summary(
                best_a.get("body_text", ""),
                text_b,
            )
            risk_kws = _risk_keywords(text_b)
            added_words, removed_words = _count_word_changes(
                best_a.get("body_text", ""), text_b
            )

            if score < _CRITICAL_THRESHOLD:
                severity = FindingSeverity.CRITICAL
                risk_score = 9
                confidence = 0.85
            elif risk_kws:
                severity = FindingSeverity.HIGH
                risk_score = 7
                confidence = 0.80
            else:
                severity = FindingSeverity.MEDIUM
                risk_score = 5
                confidence = 0.77

            word_change_note = ""
            if added_words or removed_words:
                word_change_note = (
                    f" Word-level delta: +{added_words} words added, -{removed_words} words removed."
                )

            findings.append(self._build_finding(
                flag_type="template_deviation",
                severity=severity,
                title=f"Clause altered vs. template: {clause_b.get('heading') or 'Untitled'}",
                description=(
                    f"Similarity to template clause '{best_a.get('heading') or 'Untitled'}' "
                    f"is {score:.0%} (composite score combining character, phrase, and vocabulary similarity). "
                    f"{diff_note}{word_change_note}"
                    + (f" Risk keywords detected: {', '.join(risk_kws)}." if risk_kws else "")
                ),
                recommendation=(
                    "Compare this clause against the template version carefully. "
                    "Ensure any deviations are intentional and have been legally reviewed."
                ),
                source_clause_id=str(clause_b.get("id", "")),
                confidence=confidence,
                reasoning_trace=(
                    f"composite_sim={score:.3f}; matched_template='{best_a.get('heading')}'; "
                    f"added_words={added_words}; removed_words={removed_words}"
                ),
                risk_score=risk_score,
            ))

        # ── Step 2: detect template clauses entirely missing from B ───────────
        for clause_a in clauses_a:
            text_a = (clause_a.get("body_text") or "").strip()
            if not text_a or len(text_a) < 20:
                continue
            if str(clause_a.get("id", "")) in matched_a_ids:
                continue

            _, score = _best_match(clause_a, clauses_b)
            if score < _ALTERED_THRESHOLD:
                risk_kws = _risk_keywords(text_a)
                findings.append(self._build_finding(
                    flag_type="clause_missing",
                    severity=FindingSeverity.HIGH,
                    title=f"Template clause missing from draft: {clause_a.get('heading') or 'Untitled'}",
                    description=(
                        f"This clause from the master template is absent or substantially removed "
                        f"from the proposed draft (best match: {score:.0%})."
                        + (f" This clause contained risk keywords: {', '.join(risk_kws)}." if risk_kws else "")
                    ),
                    recommendation=(
                        "Confirm whether this clause was intentionally omitted. "
                        "If not, re-add it from the template."
                    ),
                    source_clause_id=str(clause_a.get("id", "")),
                    confidence=0.82,
                    reasoning_trace=f"best_match_in_B={score:.3f}; below altered_threshold={_ALTERED_THRESHOLD}",
                    risk_score=7 if risk_kws else 6,
                ))

        self._log_run_complete(project_id, len(findings))

        return {
            "findings": findings,
            "token_usage": {"input_tokens": 0, "output_tokens": 0},
            "model_version": "python-composite-similarity-demo",
            "prompt_version": PROMPT_VERSION,
        }
