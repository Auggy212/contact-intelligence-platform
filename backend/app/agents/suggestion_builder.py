"""
Suggestion Builder — deterministic, offline, no API keys required.

Produces a structured `Suggestion` (original → suggested + reason) for a finding,
inspired by ClauseAI's `Modification(original_text, suggested_text, reason)` but
generated entirely from data the analysis already extracted — no LLM, no cost.

Each analysis agent already knows the "correct" answer:
  - Template comparison : the template baseline value / clause text
  - Vendor diff         : the pre-redline (draft B) value / text
  - Law validator       : the statutory recommendation + section
  - Checklist validator : the exact rule limit in the rule config

This module centralises turning that knowledge into an actionable suggested fix,
so every agent produces suggestions in one consistent shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.constants import FindingSeverity


# ─────────────────────────────────────────────────────────────────────────────
# Suggestion model
# ─────────────────────────────────────────────────────────────────────────────

# Priority derived from severity — tells a reviewer what to fix first.
_PRIORITY_BY_SEVERITY: dict[str, str] = {
    FindingSeverity.CRITICAL: "must_fix",
    FindingSeverity.HIGH:     "must_fix",
    FindingSeverity.MEDIUM:   "should_fix",
    FindingSeverity.LOW:      "optional",
    FindingSeverity.INFO:     "optional",
}


def priority_for(severity: str) -> str:
    return _PRIORITY_BY_SEVERITY.get(severity, "should_fix")


@dataclass
class Suggestion:
    """A single actionable, deterministic modification suggestion for a finding."""
    original_text: str    # what's currently in the contract (the problem)
    suggested_text: str   # the recommended correction
    reason: str           # why this fix is recommended (rule / statute / template)
    priority: str         # "must_fix" | "should_fix" | "optional"
    basis: str            # "template" | "vendor_draft" | "statute" | "checklist_rule" | "concept"

    def as_dict(self) -> dict[str, Any]:
        return {
            "original_text": self.original_text,
            "suggested_text": self.suggested_text,
            "reason": self.reason,
            "priority": self.priority,
            "basis": self.basis,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Builders — one per finding source
# ─────────────────────────────────────────────────────────────────────────────

def for_value_change(vc: Any, *, basis: str = "template") -> Suggestion:
    """
    Suggestion for a value-level change (payment 30→90, IP client→vendor, etc.).

    vc is a ValueChange. The suggestion is to revert to the baseline value
    (the template value in template comparison, or the draft-B value in vendor diff).

    `basis`:
      - "template"      → template comparison (revert to the gold-standard value)
      - "vendor_draft"  → vendor diff (reject vendor's change, keep the agreed draft)
    """
    baseline_label = "template standard" if basis == "template" else "agreed draft (pre-vendor)"

    if vc.direction == "removed":
        # A value/clause that existed was dropped — suggest re-adding it.
        suggested = f"Re-instate {vc.label}: {vc.old_display}"
        reason = (
            f"{vc.label} was present in the {baseline_label} ('{vc.old_display}') "
            f"but is absent now. Restoring it preserves the original protection."
        )
    elif vc.direction == "added":
        # A new value appeared that wasn't in the baseline — suggest review/removal.
        suggested = f"Remove or renegotiate the newly added {vc.label} ({vc.new_display})"
        reason = (
            f"{vc.label} was not specified in the {baseline_label} but is now "
            f"'{vc.new_display}'. Confirm it is acceptable or remove it."
        )
    else:
        # A value changed — suggest reverting to the baseline value.
        suggested = f"Revert {vc.label} to {vc.old_display}"
        reason = (
            f"{vc.label} was changed from '{vc.old_display}' to '{vc.new_display}'. "
            f"Reverting to '{vc.old_display}' restores the {baseline_label}."
        )

    return Suggestion(
        original_text=f"{vc.label}: {vc.new_display}",
        suggested_text=suggested,
        reason=reason,
        priority=priority_for(vc.severity),
        basis=basis,
    )


def for_missing_clause(
    *, clause_heading: str | None, template_body: str, severity: str
) -> Suggestion:
    """Suggestion for a template clause missing from the draft — re-add the clause."""
    heading = clause_heading or "the clause"
    snippet = template_body.strip()
    if len(snippet) > 400:
        snippet = snippet[:400].rstrip() + " …"
    return Suggestion(
        original_text=f"(missing) {heading}",
        suggested_text=f"Re-add the template clause '{heading}': \"{snippet}\"",
        reason=(
            f"This clause exists in the master template but is absent or substantially "
            f"removed from the draft. Re-adding it restores the intended protection."
        ),
        priority=priority_for(severity),
        basis="template",
    )


def for_concept(
    *, concept_name: str, recommendation: str, excerpt: str, severity: str
) -> Suggestion:
    """
    Suggestion for a semantic concept violation (IP reversed, liability cap removed…).

    The concept's own `recommendation` already states the correct position, so we
    surface it as the suggested fix.
    """
    snippet = (excerpt or "").strip()
    if len(snippet) > 200:
        snippet = snippet[:200].rstrip() + " …"
    return Suggestion(
        original_text=snippet or concept_name,
        suggested_text=recommendation,
        reason=(
            f"Concept-level analysis detected '{concept_name}'. "
            f"The recommended position restores standard, balanced terms."
        ),
        priority=priority_for(severity),
        basis="concept",
    )


def for_law_violation(
    *, matched_text: str | None, recommendation: str, act_name: str,
    section: str | None, severity: str
) -> Suggestion:
    """
    Suggestion for a law-validation finding. The rule's own `recommendation`
    already contains the corrective action; we attach the statutory basis.
    """
    cite = act_name
    if section:
        cite = f"{act_name} {section}"
    original = (matched_text or "").strip() or "the flagged provision"
    return Suggestion(
        original_text=original,
        suggested_text=recommendation,
        reason=f"Required for compliance with {cite}.",
        priority=priority_for(severity),
        basis="statute",
    )


def for_checklist(
    *, rule_name: str, detail: str, target_hint: str | None,
    extracted_value: Any, severity: str
) -> Suggestion:
    """
    Suggestion for a checklist-validation failure.

    The checklist rule config carries the exact required limit, so this is the
    most precise suggestion of all — we can state the target value directly.
    """
    current = "" if extracted_value is None else str(extracted_value)
    original = f"{rule_name}: {current}".strip().rstrip(":")
    if target_hint:
        suggested = f"Change {rule_name} to {target_hint}"
    else:
        suggested = f"Adjust {rule_name} to satisfy the checklist rule"
    return Suggestion(
        original_text=original,
        suggested_text=suggested,
        reason=detail,
        priority=priority_for(severity),
        basis="checklist_rule",
    )
