"""
Unit tests for suggestion_builder.py

Verifies deterministic modification suggestions for every finding source:
  - value change (template + vendor_draft basis)
  - missing clause
  - concept violation
  - law violation
  - checklist failure
Plus priority derivation from severity.
"""

from app.agents import suggestion_builder as sb
from app.agents.clause_analyzer import ValueChange
from app.core.constants import FindingSeverity


# ─────────────────────────────────────────────────────────────────────────────
# Priority derivation
# ─────────────────────────────────────────────────────────────────────────────

class TestPriority:
    def test_critical_is_must_fix(self):
        assert sb.priority_for(FindingSeverity.CRITICAL) == "must_fix"

    def test_high_is_must_fix(self):
        assert sb.priority_for(FindingSeverity.HIGH) == "must_fix"

    def test_medium_is_should_fix(self):
        assert sb.priority_for(FindingSeverity.MEDIUM) == "should_fix"

    def test_low_is_optional(self):
        assert sb.priority_for(FindingSeverity.LOW) == "optional"

    def test_info_is_optional(self):
        assert sb.priority_for(FindingSeverity.INFO) == "optional"

    def test_unknown_defaults_should_fix(self):
        assert sb.priority_for("banana") == "should_fix"


# ─────────────────────────────────────────────────────────────────────────────
# Value change suggestions
# ─────────────────────────────────────────────────────────────────────────────

def _vc(direction="increased", severity=FindingSeverity.HIGH,
        old_display="30 days", new_display="90 days", label="Payment Terms"):
    return ValueChange(
        field="payment_days",
        label=label,
        old_value=30.0,
        new_value=90.0,
        old_display=old_display,
        new_display=new_display,
        change_pct=200.0,
        direction=direction,
        severity=severity,
        risk_score=7,
        explanation="Payment Terms changed.",
        clause_type="payment",
        change_category="temporal",
        evidence="…",
    )


class TestValueChangeSuggestion:
    def test_changed_value_suggests_revert_to_template(self):
        s = sb.for_value_change(_vc(direction="increased"), basis="template")
        assert "Revert Payment Terms to 30 days" in s.suggested_text
        assert "template standard" in s.reason
        assert s.basis == "template"
        assert s.priority == "must_fix"

    def test_changed_value_vendor_basis_mentions_draft(self):
        s = sb.for_value_change(_vc(direction="increased"), basis="vendor_draft")
        assert "Revert Payment Terms to 30 days" in s.suggested_text
        assert "agreed draft" in s.reason
        assert s.basis == "vendor_draft"

    def test_removed_value_suggests_reinstate(self):
        vc = _vc(direction="removed", old_display="12 months", new_display="not specified",
                 label="Liability Cap")
        s = sb.for_value_change(vc, basis="template")
        assert "Re-instate Liability Cap" in s.suggested_text
        assert "12 months" in s.suggested_text

    def test_added_value_suggests_removal_or_renegotiate(self):
        vc = _vc(direction="added", old_display="not specified", new_display="3%",
                 label="Penalty Rate")
        s = sb.for_value_change(vc, basis="template")
        assert "Remove or renegotiate" in s.suggested_text
        assert "3%" in s.suggested_text

    def test_original_text_reflects_current_value(self):
        s = sb.for_value_change(_vc(), basis="template")
        assert "90 days" in s.original_text

    def test_as_dict_has_all_keys(self):
        s = sb.for_value_change(_vc(), basis="template")
        d = s.as_dict()
        assert set(d.keys()) == {"original_text", "suggested_text", "reason", "priority", "basis"}


# ─────────────────────────────────────────────────────────────────────────────
# Missing clause suggestions
# ─────────────────────────────────────────────────────────────────────────────

class TestMissingClauseSuggestion:
    def test_suggests_readding_clause(self):
        s = sb.for_missing_clause(
            clause_heading="LIABILITY CAP",
            template_body="The aggregate liability shall not exceed 12 months fees.",
            severity=FindingSeverity.HIGH,
        )
        assert "Re-add the template clause 'LIABILITY CAP'" in s.suggested_text
        assert "aggregate liability" in s.suggested_text
        assert s.basis == "template"
        assert s.priority == "must_fix"

    def test_long_body_is_truncated(self):
        long_body = "x " * 500
        s = sb.for_missing_clause(
            clause_heading="SCOPE", template_body=long_body, severity=FindingSeverity.MEDIUM
        )
        assert "…" in s.suggested_text
        assert s.priority == "should_fix"

    def test_missing_heading_uses_placeholder(self):
        s = sb.for_missing_clause(
            clause_heading=None, template_body="Some clause text here.",
            severity=FindingSeverity.HIGH,
        )
        assert "the clause" in s.suggested_text


# ─────────────────────────────────────────────────────────────────────────────
# Concept suggestions
# ─────────────────────────────────────────────────────────────────────────────

class TestConceptSuggestion:
    def test_uses_concept_recommendation(self):
        s = sb.for_concept(
            concept_name="IP ownership reversed",
            recommendation="IP must vest in the Client upon full payment.",
            excerpt="All IP shall remain the property of the Vendor.",
            severity=FindingSeverity.CRITICAL,
        )
        assert s.suggested_text == "IP must vest in the Client upon full payment."
        assert "IP ownership reversed" in s.reason
        assert s.basis == "concept"
        assert s.priority == "must_fix"

    def test_long_excerpt_truncated(self):
        s = sb.for_concept(
            concept_name="X", recommendation="Fix it.",
            excerpt="y " * 300, severity=FindingSeverity.LOW,
        )
        assert "…" in s.original_text
        assert s.priority == "optional"


# ─────────────────────────────────────────────────────────────────────────────
# Law violation suggestions
# ─────────────────────────────────────────────────────────────────────────────

class TestLawSuggestion:
    def test_cites_act_and_section(self):
        s = sb.for_law_violation(
            matched_text="ninety (90) days",
            recommendation="Reduce payment terms to 45 days.",
            act_name="MSME Development Act, 2006",
            section="Section 15",
            severity=FindingSeverity.HIGH,
        )
        assert s.suggested_text == "Reduce payment terms to 45 days."
        assert "MSME Development Act, 2006 Section 15" in s.reason
        assert s.basis == "statute"
        assert s.original_text == "ninety (90) days"

    def test_no_matched_text_uses_placeholder(self):
        s = sb.for_law_violation(
            matched_text=None, recommendation="Add a governing law clause.",
            act_name="Indian Contract Act, 1872", section=None,
            severity=FindingSeverity.HIGH,
        )
        assert s.original_text == "the flagged provision"
        assert "Indian Contract Act, 1872" in s.reason


# ─────────────────────────────────────────────────────────────────────────────
# Checklist suggestions
# ─────────────────────────────────────────────────────────────────────────────

class TestChecklistSuggestion:
    def test_uses_target_hint(self):
        s = sb.for_checklist(
            rule_name="Advance Payment %",
            detail="Advance payment 40% exceeds maximum 10%",
            target_hint="≤ 10%",
            extracted_value=40.0,
            severity="high",
        )
        assert "Change Advance Payment % to ≤ 10%" in s.suggested_text
        assert s.reason == "Advance payment 40% exceeds maximum 10%"
        assert s.basis == "checklist_rule"
        assert s.priority == "must_fix"

    def test_court_city_target(self):
        s = sb.for_checklist(
            rule_name="Dispute Court City",
            detail="Court city 'bengaluru' not in allowed cities",
            target_hint="Mumbai",
            extracted_value="bengaluru",
            severity="high",
        )
        assert "Change Dispute Court City to Mumbai" in s.suggested_text

    def test_no_target_hint_generic(self):
        s = sb.for_checklist(
            rule_name="Some Rule", detail="Failed.", target_hint=None,
            extracted_value=5, severity="medium",
        )
        assert "satisfy the checklist rule" in s.suggested_text
        assert s.priority == "should_fix"
