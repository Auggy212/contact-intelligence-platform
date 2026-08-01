"""
Unit tests for clause_analyzer.py

Tests cover:
  - ClauseClassifier: correct ClauseType for every supported category
  - ValueExtractor: digit forms, word forms, Indian monetary values, dates,
    type-specific extraction branches (Priority 2 & 3)
  - ValueDiffEngine: numeric diffs, categorical diffs, severity thresholds,
    value-removal findings, new fields (Priority 1)
  - ConfidenceScorer: evidence-based scoring
"""

import pytest
from app.agents.clause_analyzer import (
    ClauseClassifier,
    ClauseType,
    ConfidenceScorer,
    ValueChange,
    ValueDiffEngine,
    ValueExtractor,
    build_value_change_evidence,
)


# ─────────────────────────────────────────────────────────────────────────────
# CLAUSE CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────

class TestClauseClassifier:

    def _make(self, heading: str = "", body: str = "") -> dict:
        return {"heading": heading, "body_text": body}

    def test_payment_by_heading(self):
        assert ClauseClassifier.classify(self._make("PAYMENT TERMS")) == ClauseType.PAYMENT

    def test_payment_by_body(self):
        c = self._make(body="The Client shall pay the Vendor within thirty (30) days of receipt of invoice.")
        assert ClauseClassifier.classify(c) == ClauseType.PAYMENT

    def test_termination_by_heading(self):
        assert ClauseClassifier.classify(self._make("TERMINATION")) == ClauseType.TERMINATION

    def test_termination_by_body(self):
        c = self._make(body="Either Party may terminate this Agreement by giving sixty (60) days written notice.")
        assert ClauseClassifier.classify(c) == ClauseType.TERMINATION

    def test_liability_by_heading(self):
        assert ClauseClassifier.classify(self._make("LIMITATION OF LIABILITY")) == ClauseType.LIABILITY

    def test_liability_by_body(self):
        c = self._make(body="The aggregate liability of either Party shall not exceed the fees paid.")
        assert ClauseClassifier.classify(c) == ClauseType.LIABILITY

    def test_indemnity_by_body(self):
        c = self._make(body="The Vendor shall indemnify and hold harmless the Client against all claims.")
        assert ClauseClassifier.classify(c) == ClauseType.INDEMNITY

    def test_confidentiality_by_heading(self):
        assert ClauseClassifier.classify(self._make("CONFIDENTIALITY")) == ClauseType.CONFIDENTIALITY

    def test_ip_by_heading(self):
        assert ClauseClassifier.classify(self._make("INTELLECTUAL PROPERTY RIGHTS")) == ClauseType.INTELLECTUAL_PROPERTY

    def test_ip_by_body(self):
        c = self._make(body="All IP rights shall vest in the Client upon full payment of fees.")
        assert ClauseClassifier.classify(c) == ClauseType.INTELLECTUAL_PROPERTY

    def test_jurisdiction_by_body(self):
        c = self._make(body="The courts at Mumbai shall have exclusive jurisdiction over any dispute.")
        assert ClauseClassifier.classify(c) == ClauseType.JURISDICTION

    def test_data_protection_by_heading(self):
        assert ClauseClassifier.classify(self._make("DATA PROTECTION AND CYBERSECURITY")) == ClauseType.DATA_PROTECTION

    def test_force_majeure(self):
        assert ClauseClassifier.classify(self._make("FORCE MAJEURE")) == ClauseType.FORCE_MAJEURE

    def test_dispute_resolution(self):
        c = self._make(body="Disputes shall be referred to arbitration under the Arbitration and Conciliation Act, 1996.")
        assert ClauseClassifier.classify(c) == ClauseType.DISPUTE_RESOLUTION

    def test_non_compete_by_body(self):
        c = self._make(body="The Client shall not carry on any business that competes with the Vendor for 24 months.")
        assert ClauseClassifier.classify(c) == ClauseType.NON_COMPETE

    def test_non_solicitation_by_body(self):
        c = self._make(body="The Client shall not directly or indirectly solicit any employee of the Vendor.")
        assert ClauseClassifier.classify(c) == ClauseType.NON_SOLICITATION

    def test_assignment_by_body(self):
        c = self._make(body="Neither Party may assign this Agreement without the prior written consent of the other.")
        assert ClauseClassifier.classify(c) == ClauseType.ASSIGNMENT

    def test_warranty_by_heading(self):
        assert ClauseClassifier.classify(self._make("WARRANTIES AND REPRESENTATIONS")) == ClauseType.WARRANTY

    def test_sla_by_heading(self):
        assert ClauseClassifier.classify(self._make("SERVICE LEVEL AGREEMENT")) == ClauseType.SLA

    def test_insurance_by_heading(self):
        assert ClauseClassifier.classify(self._make("INSURANCE")) == ClauseType.INSURANCE

    def test_audit_rights_by_heading(self):
        assert ClauseClassifier.classify(self._make("AUDIT RIGHTS")) == ClauseType.AUDIT_RIGHTS

    def test_exclusivity_by_heading(self):
        assert ClauseClassifier.classify(self._make("EXCLUSIVITY")) == ClauseType.EXCLUSIVITY

    def test_governing_law_by_heading(self):
        assert ClauseClassifier.classify(self._make("GOVERNING LAW")) == ClauseType.GOVERNING_LAW

    def test_renewal_by_heading(self):
        assert ClauseClassifier.classify(self._make("RENEWAL AND EXTENSION")) == ClauseType.RENEWAL

    def test_service_credits_by_heading(self):
        assert ClauseClassifier.classify(self._make("SERVICE CREDITS")) == ClauseType.SERVICE_CREDITS

    def test_subcontracting_by_heading(self):
        assert ClauseClassifier.classify(self._make("SUBCONTRACTING")) == ClauseType.SUBCONTRACTING

    def test_data_retention_by_heading(self):
        assert ClauseClassifier.classify(self._make("DATA RETENTION")) == ClauseType.DATA_RETENTION

    def test_miscellaneous_fallback(self):
        c = self._make(heading="Schedule 1", body="Please see attached for scope details.")
        assert ClauseClassifier.classify(c) == ClauseType.MISCELLANEOUS

    def test_classify_all_adds_clause_type_key(self):
        clauses = [
            {"heading": "PAYMENT TERMS", "body_text": "Invoice within 30 days."},
            {"heading": "TERMINATION", "body_text": "60 days notice required."},
        ]
        result = ClauseClassifier.classify_all(clauses)
        assert result[0]["clause_type"] == "payment"
        assert result[1]["clause_type"] == "termination"

    def test_classify_all_preserves_original_fields(self):
        clauses = [{"id": "abc-123", "heading": "PAYMENT TERMS", "body_text": "30 days."}]
        result = ClauseClassifier.classify_all(clauses)
        assert result[0]["id"] == "abc-123"


# ─────────────────────────────────────────────────────────────────────────────
# VALUE EXTRACTOR — core fields
# ─────────────────────────────────────────────────────────────────────────────

class TestValueExtractor:

    def setup_method(self):
        self.ex = ValueExtractor()

    def _extract(self, text: str, ctype: ClauseType = ClauseType.MISCELLANEOUS):
        return self.ex.extract(text, ctype)

    # ── Duration ─────────────────────────────────────────────────────────────

    def test_duration_digit_months(self):
        ev = self._extract("shall remain in force for 24 months.")
        assert ev.duration_months == 24.0

    def test_duration_word_months(self):
        ev = self._extract("shall remain in force for twenty-four (24) months.")
        assert ev.duration_months == 24.0

    def test_duration_forty_eight_months(self):
        ev = self._extract("shall remain in force for forty-eight (48) months.")
        assert ev.duration_months == 48.0

    def test_duration_thirty_six_months(self):
        ev = self._extract("term of thirty-six (36) months.")
        assert ev.duration_months == 36.0

    def test_duration_sixty_months(self):
        # Realistic contract phrasing ("term of ...") rather than the degenerate
        # "60 months term" — the value extractor is scoped by leading context
        # hints ("term of", "period of") to avoid grabbing unrelated durations.
        ev = self._extract("The term of sixty (60) months applies.")
        assert ev.duration_months == 60.0

    def test_duration_years(self):
        ev = self._extract("for a period of two (2) years.")
        assert ev.duration_months == 24.0

    # ── Payment days ─────────────────────────────────────────────────────────

    def test_payment_days_digit(self):
        ev = self._extract("The Client shall pay within 30 days of receipt of invoice.", ClauseType.PAYMENT)
        assert ev.payment_days == 30.0

    def test_payment_days_ninety_word(self):
        ev = self._extract(
            "The Client shall pay within ninety (90) days of receipt of a valid GST invoice.",
            ClauseType.PAYMENT,
        )
        assert ev.payment_days == 90.0

    def test_payment_days_forty_five(self):
        ev = self._extract("shall pay within forty-five (45) days of invoice.", ClauseType.PAYMENT)
        assert ev.payment_days == 45.0

    def test_late_payment_interest_extracted(self):
        ev = self._extract(
            "Late payment interest at the rate of 18% per annum shall be charged.",
            ClauseType.PAYMENT,
        )
        assert ev.late_payment_interest == 18.0

    # ── Advance % ────────────────────────────────────────────────────────────

    def test_advance_digit(self):
        ev = self._extract("Advance payment shall not exceed 10% of the total contract value.", ClauseType.PAYMENT)
        assert ev.advance_percent == 10.0

    def test_advance_word(self):
        ev = self._extract(
            "Advance payment shall not exceed thirty percent (30%) of the total contract value.",
            ClauseType.PAYMENT,
        )
        assert ev.advance_percent == 30.0

    def test_advance_forty(self):
        ev = self._extract("Advance payment shall not exceed forty percent (40%) of the total.", ClauseType.PAYMENT)
        assert ev.advance_percent == 40.0

    # ── Contract value ────────────────────────────────────────────────────────

    def test_value_lakhs_digit(self):
        ev = self._extract("total contract value shall not exceed ₹50,00,000 excluding taxes.")
        assert ev.contract_value_inr == 5_000_000.0

    def test_value_one_crore_word(self):
        ev = self._extract("total contract value shall not exceed Indian Rupees One Crore (Rs.1,00,00,000).")
        assert ev.contract_value_inr == 10_000_000.0

    def test_value_seventy_five_lakhs(self):
        ev = self._extract("total contract value shall not exceed Indian Rupees Seventy-Five Lakhs.")
        assert ev.contract_value_inr == 7_500_000.0

    def test_value_one_crore_fifty_lakhs(self):
        ev = self._extract("total contract value Indian Rupees One Crore Fifty Lakhs (₹1,50,00,000).")
        assert ev.contract_value_inr == 15_000_000.0

    # ── Termination notice ───────────────────────────────────────────────────

    def test_notice_digit_days(self):
        ev = self._extract(
            "Either Party may terminate on sixty (60) days' prior written notice.",
            ClauseType.TERMINATION,
        )
        assert ev.notice_days == 60.0

    def test_notice_fifteen_days(self):
        ev = self._extract(
            "terminate without cause by providing fifteen (15) days prior written notice.",
            ClauseType.TERMINATION,
        )
        assert ev.notice_days == 15.0

    def test_notice_seven_days(self):
        ev = self._extract("terminate without cause on seven (7) days' notice.", ClauseType.TERMINATION)
        assert ev.notice_days == 7.0

    # ── Court city ───────────────────────────────────────────────────────────

    def test_court_mumbai(self):
        ev = self._extract("The courts at Mumbai shall have exclusive jurisdiction.", ClauseType.JURISDICTION)
        assert ev.court_city == "mumbai"

    def test_court_new_delhi(self):
        ev = self._extract("The courts at New Delhi shall have exclusive jurisdiction.", ClauseType.JURISDICTION)
        assert ev.court_city == "new delhi"

    def test_court_bengaluru(self):
        ev = self._extract("courts of Bengaluru shall have exclusive jurisdiction.", ClauseType.JURISDICTION)
        assert ev.court_city == "bengaluru"

    # ── IP ownership ─────────────────────────────────────────────────────────

    def test_ip_owner_client(self):
        ev = self._extract(
            "All IP created by Vendor shall vest in the Client upon full payment.",
            ClauseType.INTELLECTUAL_PROPERTY,
        )
        assert ev.ip_owner == "client"

    def test_ip_owner_vendor(self):
        ev = self._extract(
            "All IP shall remain the exclusive property of the Vendor.",
            ClauseType.INTELLECTUAL_PROPERTY,
        )
        assert ev.ip_owner == "vendor"

    # ── Indemnity direction ──────────────────────────────────────────────────

    def test_indemnity_vendor_to_client(self):
        ev = self._extract(
            "The Vendor shall indemnify the Client against all third-party claims.",
            ClauseType.INDEMNITY,
        )
        assert ev.indemnity_direction == "vendor_to_client"

    def test_indemnity_client_to_vendor(self):
        ev = self._extract(
            "The Client shall fully indemnify and hold harmless the Vendor.",
            ClauseType.INDEMNITY,
        )
        assert ev.indemnity_direction == "client_to_vendor"

    # ── Liability cap ────────────────────────────────────────────────────────

    def test_liability_cap_months(self):
        ev = self._extract(
            "The aggregate liability of either Party shall not exceed the total fees paid "
            "in the twelve (12) months immediately preceding the event.",
            ClauseType.LIABILITY,
        )
        assert ev.liability_cap_months == 12.0

    def test_liability_cap_six_months(self):
        ev = self._extract(
            "aggregate liability shall not exceed the fees paid in the six (6) months preceding the claim.",
            ClauseType.LIABILITY,
        )
        assert ev.liability_cap_months == 6.0


# ─────────────────────────────────────────────────────────────────────────────
# VALUE EXTRACTOR — type-specific fields (Priority 3)
# ─────────────────────────────────────────────────────────────────────────────

class TestValueExtractorTypeSpecific:

    def setup_method(self):
        self.ex = ValueExtractor()

    # ── SLA clause ───────────────────────────────────────────────────────────

    def test_sla_uptime_percent_extracted(self):
        ev = self.ex.extract(
            "The Vendor guarantees a monthly uptime of 99.9% for the platform.",
            ClauseType.SLA,
        )
        assert ev.sla_uptime_percent == 99.9

    def test_sla_response_time_hours(self):
        ev = self.ex.extract(
            "Initial response to P1 incidents shall be within four (4) hours of acknowledgement.",
            ClauseType.SLA,
        )
        assert ev.sla_response_time_hours == 4.0

    def test_sla_response_time_minutes_converted(self):
        ev = self.ex.extract(
            "The Vendor shall acknowledge all P1 tickets within 30 minutes.",
            ClauseType.SLA,
        )
        assert ev.sla_response_time_hours is not None
        assert abs(ev.sla_response_time_hours - 0.5) < 0.01

    # ── Warranty clause ───────────────────────────────────────────────────────

    def test_warranty_days_digit(self):
        ev = self.ex.extract(
            "The Vendor warrants that deliverables shall be defect-free for ninety (90) days.",
            ClauseType.WARRANTY,
        )
        assert ev.warranty_days == 90.0

    def test_warranty_months_converted_to_days(self):
        ev = self.ex.extract(
            "Warranty period of three (3) months from acceptance.",
            ClauseType.WARRANTY,
        )
        assert ev.warranty_days == 90.0

    # ── Insurance clause ──────────────────────────────────────────────────────

    def test_insurance_amount_inr(self):
        ev = self.ex.extract(
            "The Vendor shall maintain professional indemnity insurance of at least ₹2 Crore.",
            ClauseType.INSURANCE,
        )
        assert ev.insurance_amount_inr == 2e7

    # ── Non-compete clause ───────────────────────────────────────────────────

    def test_non_compete_duration(self):
        ev = self.ex.extract(
            "The Client shall not carry on any competing business for a non-compete period of 24 months.",
            ClauseType.NON_COMPETE,
        )
        assert ev.non_compete_months == 24.0

    def test_non_compete_years_converted(self):
        ev = self.ex.extract(
            "Non-compete restriction applies for two (2) years after termination.",
            ClauseType.NON_COMPETE,
        )
        assert ev.non_compete_months == 24.0

    # ── Non-solicitation clause ───────────────────────────────────────────────

    def test_non_solicitation_duration(self):
        ev = self.ex.extract(
            "Non-solicitation restriction shall apply for twelve (12) months.",
            ClauseType.NON_SOLICITATION,
        )
        assert ev.non_solicitation_months == 12.0

    # ── Data retention clause ─────────────────────────────────────────────────

    def test_data_retention_days(self):
        ev = self.ex.extract(
            "The Vendor shall retain all personal data for a period of thirty (30) days after termination.",
            ClauseType.DATA_RETENTION,
        )
        assert ev.data_retention_days == 30.0

    def test_data_retention_months_converted(self):
        ev = self.ex.extract(
            "Data retention period shall not exceed six (6) months.",
            ClauseType.DATA_RETENTION,
        )
        assert ev.data_retention_days == 180.0

    # ── Assignment clause ─────────────────────────────────────────────────────

    def test_assignment_consent_required(self):
        ev = self.ex.extract(
            "Neither Party may assign this Agreement without the prior written consent of the other.",
            ClauseType.ASSIGNMENT,
        )
        assert ev.assignment_consent == "required"

    def test_assignment_consent_not_required(self):
        ev = self.ex.extract(
            "Either Party may freely assign this Agreement to its affiliates.",
            ClauseType.ASSIGNMENT,
        )
        assert ev.assignment_consent == "not_required"

    # ── Renewal clause ────────────────────────────────────────────────────────

    def test_renewal_opt_out_notice(self):
        ev = self.ex.extract(
            "The Agreement shall automatically renew unless written notice of non-renewal "
            "is provided at least thirty (30) days before expiry.",
            ClauseType.RENEWAL,
        )
        assert ev.renewal_notice_days == 30.0

    # ── Service credits ───────────────────────────────────────────────────────

    def test_service_credit_percent(self):
        ev = self.ex.extract(
            "Service credits of 5% of the monthly fee apply for each hour of downtime beyond the SLA.",
            ClauseType.SERVICE_CREDITS,
        )
        assert ev.service_credit_percent == 5.0

    # ── Audit frequency ───────────────────────────────────────────────────────

    def test_audit_frequency_annual(self):
        ev = self.ex.extract(
            "The Client may conduct an audit once every twelve (12) months.",
            ClauseType.AUDIT_RIGHTS,
        )
        assert ev.audit_frequency_months == 12.0

    # ── Governing law ─────────────────────────────────────────────────────────

    def test_governing_law_india(self):
        ev = self.ex.extract(
            "This Agreement shall be governed by the laws of India.",
            ClauseType.GOVERNING_LAW,
        )
        assert ev.governing_law is not None
        assert "india" in ev.governing_law.lower()

    def test_arbitration_seat(self):
        ev = self.ex.extract(
            "The seat of arbitration shall be Mumbai.",
            ClauseType.JURISDICTION,
        )
        assert ev.arbitration_seat == "mumbai"

    # ── Subcontracting ────────────────────────────────────────────────────────

    def test_subcontracting_consent_required(self):
        ev = self.ex.extract(
            "The Vendor may not subcontract any part of the Services without prior written approval.",
            ClauseType.SUBCONTRACTING,
        )
        assert ev.subcontracting_consent == "required"


# ─────────────────────────────────────────────────────────────────────────────
# VALUE DIFF ENGINE — core diffs
# ─────────────────────────────────────────────────────────────────────────────

class TestValueDiffEngine:

    def setup_method(self):
        self.engine = ValueDiffEngine()

    def _diff(self, text_a: str, text_b: str, ctype: ClauseType = ClauseType.PAYMENT) -> list:
        ca = {"body_text": text_a}
        cb = {"body_text": text_b}
        return self.engine.diff(ca, cb, ctype)

    # ── Payment days ─────────────────────────────────────────────────────────

    def test_payment_30_to_90_detected(self):
        changes = self._diff(
            "The Client shall pay within thirty (30) days of receipt of invoice.",
            "The Client shall pay within ninety (90) days of receipt of invoice.",
        )
        pay_changes = [c for c in changes if c.field == "payment_days"]
        assert len(pay_changes) >= 1
        vc = pay_changes[0]
        assert vc.old_value == 30.0
        assert vc.new_value == 90.0
        assert vc.direction == "increased"
        assert vc.severity in ("high", "critical")

    def test_payment_30_to_45_detected(self):
        changes = self._diff(
            "The Client shall pay within 30 days of invoice.",
            "The Client shall pay within 45 days of invoice.",
        )
        pay_changes = [c for c in changes if c.field == "payment_days"]
        assert len(pay_changes) >= 1

    def test_payment_unchanged_no_finding(self):
        changes = self._diff(
            "The Client shall pay within 30 days of invoice.",
            "The Client shall pay within 30 days of invoice.",
        )
        pay_changes = [c for c in changes if c.field == "payment_days"]
        assert len(pay_changes) == 0

    # ── Advance payment ───────────────────────────────────────────────────────

    def test_advance_10_to_30_detected(self):
        changes = self._diff(
            "Advance payment shall not exceed 10% of the total.",
            "Advance payment shall not exceed thirty percent (30%) of the total.",
            ClauseType.PAYMENT,
        )
        adv = [c for c in changes if c.field == "advance_percent"]
        assert len(adv) >= 1
        assert adv[0].old_value == 10.0
        assert adv[0].new_value == 30.0
        assert adv[0].severity == "high"

    # ── Termination notice ────────────────────────────────────────────────────

    def test_notice_60_to_15_detected(self):
        changes = self._diff(
            "Either Party may terminate on sixty (60) days' prior written notice.",
            "Either Party may terminate on fifteen (15) days' prior written notice.",
            ClauseType.TERMINATION,
        )
        notice = [c for c in changes if c.field == "notice_days"]
        assert len(notice) >= 1
        assert notice[0].old_value == 60.0
        assert notice[0].new_value == 15.0
        assert notice[0].direction == "decreased"

    # ── Liability cap ─────────────────────────────────────────────────────────

    def test_liability_cap_12_to_6_months(self):
        changes = self._diff(
            "aggregate liability shall not exceed fees paid in twelve (12) months.",
            "aggregate liability shall not exceed fees paid in six (6) months.",
            ClauseType.LIABILITY,
        )
        cap = [c for c in changes if c.field == "liability_cap_months"]
        assert len(cap) >= 1
        assert cap[0].old_value == 12.0
        assert cap[0].new_value == 6.0

    # ── Contract value ────────────────────────────────────────────────────────

    def test_contract_value_50L_to_1cr(self):
        changes = self._diff(
            "contract value shall not exceed Indian Rupees Fifty Lakhs (₹50,00,000).",
            "contract value shall not exceed Indian Rupees One Crore (₹1,00,00,000).",
            ClauseType.PAYMENT,
        )
        val = [c for c in changes if c.field == "contract_value_inr"]
        assert len(val) >= 1
        assert val[0].old_value == 5_000_000.0
        assert val[0].new_value == 10_000_000.0
        assert val[0].direction == "increased"

    # ── Court city ────────────────────────────────────────────────────────────

    def test_court_mumbai_to_delhi(self):
        changes = self._diff(
            "courts at Mumbai shall have exclusive jurisdiction.",
            "courts at New Delhi shall have exclusive jurisdiction.",
            ClauseType.JURISDICTION,
        )
        court = [c for c in changes if c.field == "court_city"]
        assert len(court) >= 1
        assert court[0].old_value == "mumbai"
        assert court[0].new_value == "new delhi"
        assert court[0].severity == "high"

    # ── IP ownership reversal ─────────────────────────────────────────────────

    def test_ip_client_to_vendor(self):
        changes = self._diff(
            "All IP shall vest in the Client upon full payment.",
            "All IP shall remain the exclusive property of the Vendor.",
            ClauseType.INTELLECTUAL_PROPERTY,
        )
        ip = [c for c in changes if c.field == "ip_owner"]
        assert len(ip) >= 1
        assert ip[0].old_value == "client"
        assert ip[0].new_value == "vendor"

    # ── Identical clauses produce no changes ─────────────────────────────────

    def test_identical_clauses_no_changes(self):
        text = (
            "The Client shall pay within thirty (30) days of receipt of invoice. "
            "Advance payment shall not exceed ten percent (10%)."
        )
        changes = self._diff(text, text)
        assert len(changes) == 0


# ─────────────────────────────────────────────────────────────────────────────
# VALUE DIFF ENGINE — Priority 1 enhancements
# ─────────────────────────────────────────────────────────────────────────────

class TestValueDiffEngineEnhancements:

    def setup_method(self):
        self.engine = ValueDiffEngine()

    def _diff(self, text_a: str, text_b: str, ctype: ClauseType = ClauseType.MISCELLANEOUS) -> list:
        return self.engine.diff({"body_text": text_a}, {"body_text": text_b}, ctype)

    # ── SLA uptime change ─────────────────────────────────────────────────────

    def test_sla_uptime_99_to_95(self):
        changes = self._diff(
            "The platform shall maintain a monthly uptime of 99.9%.",
            "The platform shall maintain a monthly uptime of 95%.",
            ClauseType.SLA,
        )
        sla = [c for c in changes if c.field == "sla_uptime_percent"]
        assert len(sla) >= 1
        assert sla[0].old_value == 99.9
        assert sla[0].new_value == 95.0
        assert sla[0].direction == "decreased"
        assert sla[0].severity in ("high", "critical")

    def test_sla_uptime_absolute_trigger_below_95(self):
        changes = self._diff(
            "Uptime guarantee: 99%.",
            "Uptime guarantee: 90%.",
            ClauseType.SLA,
        )
        sla = [c for c in changes if c.field == "sla_uptime_percent"]
        assert any(c.severity in ("high", "critical") for c in sla)

    # ── SLA response time change ──────────────────────────────────────────────

    def test_sla_response_time_2h_to_8h(self):
        changes = self._diff(
            "Initial response to P1 incidents within two (2) hours.",
            "Initial response to P1 incidents within eight (8) hours.",
            ClauseType.SLA,
        )
        resp = [c for c in changes if c.field == "sla_response_time_hours"]
        assert len(resp) >= 1
        assert resp[0].old_value == 2.0
        assert resp[0].new_value == 8.0
        assert resp[0].direction == "increased"

    # ── Warranty period change ────────────────────────────────────────────────

    def test_warranty_90_to_30_days(self):
        changes = self._diff(
            "Deliverables warranted defect-free for ninety (90) days.",
            "Deliverables warranted defect-free for thirty (30) days.",
            ClauseType.WARRANTY,
        )
        war = [c for c in changes if c.field == "warranty_days"]
        assert len(war) >= 1
        assert war[0].old_value == 90.0
        assert war[0].new_value == 30.0

    def test_warranty_below_30_triggers_high(self):
        changes = self._diff(
            "Warranty period of 90 days.",
            "Warranty period of 14 days.",
            ClauseType.WARRANTY,
        )
        war = [c for c in changes if c.field == "warranty_days"]
        assert any(c.severity in ("high", "critical") for c in war)

    # ── Value removal detection (Priority 1 core requirement) ────────────────

    def test_liability_cap_removed_fires_finding(self):
        """When a liability cap existed in A but is gone from B, always report it."""
        changes = self._diff(
            "The aggregate liability of either Party shall not exceed the fees paid "
            "in the twelve (12) months preceding the event.",
            "Either party may have unlimited liability under this agreement.",
            ClauseType.LIABILITY,
        )
        removed = [c for c in changes if c.field == "liability_cap_months" and c.direction == "removed"]
        assert len(removed) >= 1
        assert removed[0].severity == "high"

    def test_sla_uptime_removed_fires_finding(self):
        """SLA uptime commitment removed from new version → finding."""
        changes = self._diff(
            "Monthly uptime of 99.5% guaranteed.",
            "The vendor will use best efforts to maintain the service.",
            ClauseType.SLA,
        )
        removed = [c for c in changes if c.field == "sla_uptime_percent" and c.direction == "removed"]
        assert len(removed) >= 1

    def test_warranty_removed_fires_finding(self):
        """Warranty period removed → finding."""
        changes = self._diff(
            "Deliverables are warranted free from defects for ninety (90) days.",
            "Deliverables are provided AS IS without any warranty.",
            ClauseType.WARRANTY,
        )
        removed = [c for c in changes if c.field == "warranty_days" and c.direction == "removed"]
        assert len(removed) >= 1

    # ── Non-compete duration change ───────────────────────────────────────────

    def test_non_compete_12_to_36_months(self):
        changes = self._diff(
            "Non-compete restriction applies for 12 months.",
            "Non-compete restriction applies for 36 months.",
            ClauseType.NON_COMPETE,
        )
        nc = [c for c in changes if c.field == "non_compete_months"]
        assert len(nc) >= 1
        assert nc[0].old_value == 12.0
        assert nc[0].new_value == 36.0

    def test_non_compete_above_24_triggers_high(self):
        changes = self._diff(
            "Non-compete duration of 12 months.",
            "Non-compete duration of 36 months.",
            ClauseType.NON_COMPETE,
        )
        nc = [c for c in changes if c.field == "non_compete_months"]
        assert any(c.severity in ("high", "critical") for c in nc)

    # ── Insurance amount change ───────────────────────────────────────────────

    def test_insurance_amount_change(self):
        changes = self._diff(
            "Maintain insurance of ₹2 Crore.",
            "Maintain insurance of ₹1 Crore.",
            ClauseType.INSURANCE,
        )
        ins = [c for c in changes if c.field == "insurance_amount_inr"]
        assert len(ins) >= 1
        assert ins[0].old_value == 2e7
        assert ins[0].new_value == 1e7

    # ── Service credit change ─────────────────────────────────────────────────

    def test_service_credit_reduction(self):
        changes = self._diff(
            "Service credits of 10% per hour of downtime.",
            "Service credits of 2% per hour of downtime.",
            ClauseType.SERVICE_CREDITS,
        )
        sc = [c for c in changes if c.field == "service_credit_percent"]
        assert len(sc) >= 1
        assert sc[0].direction == "decreased"

    # ── Assignment consent change ─────────────────────────────────────────────

    def test_assignment_consent_added(self):
        changes = self._diff(
            "Either party may freely assign this Agreement.",
            "Neither Party may assign this Agreement without prior written consent.",
            ClauseType.ASSIGNMENT,
        )
        asgn = [c for c in changes if c.field == "assignment_consent"]
        assert len(asgn) >= 1
        assert asgn[0].direction in ("changed", "added")

    # ── Governing law change ──────────────────────────────────────────────────

    def test_governing_law_india_to_other(self):
        changes = self._diff(
            "This Agreement shall be governed by the laws of India.",
            "This Agreement shall be governed by the laws of England.",
            ClauseType.GOVERNING_LAW,
        )
        gl = [c for c in changes if c.field == "governing_law"]
        assert len(gl) >= 1
        assert gl[0].old_value is not None
        assert "england" in gl[0].new_value.lower()

    # ── change_category and evidence fields populated ─────────────────────────

    def test_change_category_populated(self):
        changes = self._diff(
            "The Client shall pay within 30 days.",
            "The Client shall pay within 60 days.",
            ClauseType.PAYMENT,
        )
        pay = [c for c in changes if c.field == "payment_days"]
        assert len(pay) >= 1
        assert pay[0].change_category in ("temporal", "numeric", "monetary", "categorical")

    def test_evidence_field_populated(self):
        changes = self._diff(
            "The Client shall pay within 30 days.",
            "The Client shall pay within 90 days.",
            ClauseType.PAYMENT,
        )
        pay = [c for c in changes if c.field == "payment_days"]
        assert len(pay) >= 1
        assert pay[0].evidence != ""
        assert "30" in pay[0].evidence or "90" in pay[0].evidence

    # ── Evidence string format ────────────────────────────────────────────────

    def test_evidence_string_format(self):
        changes = self._diff(
            "The Client shall pay within 30 days of invoice.",
            "The Client shall pay within ninety (90) days of invoice.",
        )
        evidence = build_value_change_evidence(changes)
        assert "Payment Terms" in evidence or "payment" in evidence.lower()
        assert "30" in evidence
        assert "90" in evidence


# ─────────────────────────────────────────────────────────────────────────────
# CONFIDENCE SCORER
# ─────────────────────────────────────────────────────────────────────────────

class TestConfidenceScorer:

    def test_base_score_without_evidence(self):
        score = ConfidenceScorer.score()
        assert 0.50 <= score <= 0.60

    def test_ooxml_raises_score(self):
        without = ConfidenceScorer.score(text_similarity=0.8)
        with_ooxml = ConfidenceScorer.score(text_similarity=0.8, has_ooxml_changes=True)
        assert with_ooxml > without

    def test_heading_match_raises_score(self):
        without = ConfidenceScorer.score(text_similarity=0.7)
        with_heading = ConfidenceScorer.score(text_similarity=0.7, heading_matched=True)
        assert with_heading > without

    def test_value_changes_raise_score(self):
        base = ConfidenceScorer.score(text_similarity=0.6)
        with_vals = ConfidenceScorer.score(text_similarity=0.6, value_changes_count=3)
        assert with_vals > base

    def test_concept_match_raises_score(self):
        base = ConfidenceScorer.score()
        with_concept = ConfidenceScorer.score(concept_matched=True)
        assert with_concept > base

    def test_max_score_capped_at_97(self):
        score = ConfidenceScorer.score(
            text_similarity=1.0,
            heading_matched=True,
            has_ooxml_changes=True,
            value_changes_count=10,
            concept_matched=True,
            clause_type_known=True,
        )
        assert score <= 0.97

    def test_score_is_float_in_range(self):
        for sim in [0.0, 0.3, 0.6, 0.9, 1.0]:
            s = ConfidenceScorer.score(text_similarity=sim)
            assert 0.0 <= s <= 1.0

    def test_fully_evidenced_higher_than_guess(self):
        guess = ConfidenceScorer.score(text_similarity=0.5)
        full  = ConfidenceScorer.score(
            text_similarity=0.9,
            heading_matched=True,
            has_ooxml_changes=True,
            value_changes_count=2,
            concept_matched=True,
        )
        assert full > guess
