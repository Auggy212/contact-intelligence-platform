"""Unit tests for the checklist rules engine (no LLM calls — tests Phase 2 only)."""

import pytest
from datetime import date, timedelta

from app.agents.checklist_validator import _validate_rules

_DEFAULT_RULES = [
    {"rule_code": "A", "name": "Agreement Duration", "severity": "critical",
     "rule_config": {"min_months": 12, "max_months": 36}},
    {"rule_code": "B", "name": "Agreement Date", "severity": "critical",
     "rule_config": {}},
    {"rule_code": "C", "name": "Dispute Court", "severity": "high",
     "rule_config": {"allowed_cities": ["mumbai"]}},
    {"rule_code": "D", "name": "Advance Payment", "severity": "high",
     "rule_config": {"max_percent": 10}},
    {"rule_code": "E", "name": "Contract Value", "severity": "medium",
     "rule_config": {"max_value_inr": 5_000_000}},
    {"rule_code": "F", "name": "Termination Notice", "severity": "critical",
     "rule_config": {"min_months": 1, "max_months": 3}},
]


def test_all_rules_pass_with_valid_data():
    future = (date.today() + timedelta(days=30)).isoformat()
    extracted = {
        "agreement_duration_months": 24,
        "agreement_date": future,
        "dispute_court_city": "mumbai",
        "advance_payment_percent": 5,
        "contract_value_inr": 3_000_000,
        "termination_notice_months": 2,
    }
    failures = _validate_rules(extracted, _DEFAULT_RULES)
    assert failures == []


def test_rule_a_fails_too_short():
    failures = _validate_rules({"agreement_duration_months": 6}, _DEFAULT_RULES[:1])
    assert len(failures) == 1
    assert failures[0]["result"] == "fail"
    assert failures[0]["rule_code"] == "A"


def test_rule_a_fails_too_long():
    failures = _validate_rules({"agreement_duration_months": 48}, _DEFAULT_RULES[:1])
    assert failures[0]["result"] == "fail"


def test_rule_b_fails_past_date():
    past = (date.today() - timedelta(days=1)).isoformat()
    failures = _validate_rules({"agreement_date": past}, [_DEFAULT_RULES[1]])
    assert failures[0]["result"] == "fail"


def test_rule_b_not_found():
    failures = _validate_rules({}, [_DEFAULT_RULES[1]])
    assert failures[0]["result"] == "not_found"


def test_rule_c_fails_wrong_city():
    failures = _validate_rules({"dispute_court_city": "delhi"}, [_DEFAULT_RULES[2]])
    assert failures[0]["result"] == "fail"


def test_rule_d_fails_advance_too_high():
    failures = _validate_rules({"advance_payment_percent": 15}, [_DEFAULT_RULES[3]])
    assert failures[0]["result"] == "fail"


def test_rule_e_fails_value_too_high():
    failures = _validate_rules({"contract_value_inr": 6_000_000}, [_DEFAULT_RULES[4]])
    assert failures[0]["result"] == "fail"


def test_rule_f_fails_notice_too_long():
    failures = _validate_rules({"termination_notice_months": 6}, [_DEFAULT_RULES[5]])
    assert failures[0]["result"] == "fail"
