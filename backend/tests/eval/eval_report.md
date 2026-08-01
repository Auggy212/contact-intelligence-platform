# Contract Engine — Ground-Truth Evaluation Report

**Overall:  Recall 50%  ·  Precision 65%  ·  F1 0.57**
(True positives: 28  ·  Missed: 28  ·  Cross-field false positives tracked below)

| Section | Expected | Caught | Missed | Recall |
|---|---|---|---|---|
| Template Comparison (A vs B) | 38 | 22 | 16 | 58% |
| Vendor Diff (B vs C) | 9 | 2 | 7 | 22% |
| Law Validation (B) | 4 | 3 | 1 | 75% |
| Checklist Validation (B) | 5 | 1 | 4 | 20% |

## Missed expectations (false negatives)

**Template Comparison (A vs B)**
  - advance_percent
  - contract_value_inr
  - late_payment_interest
  - penalty_percent
  - sla_response_time_hours
  - service_credit_percent
  - confidentiality_years
  - non_compete_months
  - non_solicitation_months
  - liability_cap_months
  - renewal_notice_days
  - indemnity_direction
  - assignment_consent
  - subcontracting_consent
  - IP ownership reversed
  - Data protection weakened

**Vendor Diff (B vs C)**
  - duration_months
  - payment_days
  - advance_percent
  - sla_uptime_percent
  - warranty_days
  - confidentiality_years
  - notice_days

**Law Validation (B)**
  - governing law

**Checklist Validation (B)**
  - Court
  - Payment
  - Advance
  - Contract

## Cross-field false positives (the point-2 metric)

Value-change findings whose field is not a genuine expected change — spurious extractions.

**template_comparison: 8 spurious field(s)**
  - `interest_rate` in: [Value Change] Interest Rate: not specified → 24.0%
  - `interest_rate` in: Clause altered vs. template: Late payment interest shall accrue at the
  - `payment_days` in: [Value Change] Payment Terms: not specified → 30 days
  - `payment_days` in: Clause altered vs. template: A penalty of three percent (3%) per month
  - `ip_owner` in: [Value Change] IP Ownership: vendor → not specified
  - `ip_owner` in: Clause altered vs. template: The Client shall not reverse-engineer, de
  - `governing_law` in: [Value Change] Governing Law: india → not specified
  - `governing_law` in: Clause altered vs. template: The courts at Bengaluru shall have exclus

**vendor_diff: 7 spurious field(s)**
  - `payment_days` in: [Value Change] Payment Terms: 90 days → 30 days
  - `contract_value_inr` in: [Value Change] Contract Value: ₹1.50 Cr → ₹2
  - `warranty_days` in: [Value Change] Warranty Period: 14 days → not specified
  - `insurance_amount_inr` in: [Value Change] Insurance Requirement: not specified → ₹1
  - `confidentiality_years` in: [Value Change] Confidentiality Period: 0.5 years → 5.0 years
  - `audit_frequency_months` in: [Value Change] Audit Frequency: not specified → 36 months
  - `notice_days` in: [Value Change] Termination Notice: 7 days → 60 days

**Total spurious cross-field extractions: 15**
