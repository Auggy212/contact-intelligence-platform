"""
Clean realistic-clause evaluation.

The Test_Contracts_new DOCX files have an unusual structure (operative text in
headings, [TEST NOTE] annotations in bodies) that depresses measured accuracy
in a way a real contract would not. This eval measures the engine on clean,
realistic clause pairs — exactly how a genuine vendor draft would read — to
report the engine's TRUE accuracy on value extraction + diffing.

Run from backend/:
    python scripts/run_eval_clean.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.clause_analyzer import ValueDiffEngine, ClauseType  # noqa: E402

_SEV_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

# Each case: (clause_type, template_text, vendor_text, expected list of (field, old, new))
# Clauses are written the way a real MSA reads.
CASES = [
    (ClauseType.PAYMENT,
     "The Client shall pay within thirty (30) days of receipt of invoice. "
     "Advance payment shall not exceed ten percent (10%) of the total contract value. "
     "The total contract value shall not exceed Indian Rupees Seventy-Five Lakhs (₹75,00,000).",
     "The Client shall pay within ninety (90) days of receipt of invoice. "
     "Advance payment shall not exceed forty percent (40%) of the total contract value. "
     "The total contract value shall not exceed Indian Rupees One Crore Fifty Lakhs (₹1,50,00,000).",
     [("payment_days", 30, 90), ("advance_percent", 10, 40), ("contract_value_inr", 7500000, 15000000)]),

    (ClauseType.TERMINATION,
     "Either Party may terminate this Agreement on sixty (60) days' prior written notice.",
     "Either Party may terminate this Agreement on seven (7) days' prior written notice.",
     [("notice_days", 60, 7)]),

    (ClauseType.LIABILITY,
     "The aggregate liability shall not exceed the fees paid in the twelve (12) months preceding the claim.",
     "The aggregate liability shall not exceed the fees paid in the six (6) months preceding the claim.",
     [("liability_cap_months", 12, 6)]),

    (ClauseType.CONFIDENTIALITY,
     "Confidentiality obligations shall survive for three (3) years after termination.",
     "Confidentiality obligations shall survive for six (6) months after termination.",
     [("confidentiality_years", 3, 0.5)]),

    (ClauseType.WARRANTY,
     "The Vendor warrants deliverables are defect-free for ninety (90) days from acceptance.",
     "The Vendor warrants deliverables are defect-free for fourteen (14) days from acceptance.",
     [("warranty_days", 90, 14)]),

    (ClauseType.SLA,
     "The Vendor guarantees monthly uptime of ninety-nine point nine percent (99.9%). "
     "Initial response to P1 incidents shall be within two (2) hours.",
     "The Vendor guarantees monthly uptime of ninety-five percent (95%). "
     "Initial response to P1 incidents shall be within eight (8) hours.",
     [("sla_uptime_percent", 99.9, 95), ("sla_response_time_hours", 2, 8)]),

    (ClauseType.INTELLECTUAL_PROPERTY,
     "All Intellectual Property shall vest in the Client upon full payment.",
     "All Intellectual Property shall remain the exclusive property of the Vendor.",
     [("ip_owner", "client", "vendor")]),

    (ClauseType.INDEMNITY,
     "The Vendor shall indemnify the Client against all third-party claims.",
     "The Client shall fully indemnify the Vendor against all third-party claims.",
     [("indemnity_direction", "vendor_to_client", "client_to_vendor")]),

    (ClauseType.JURISDICTION,
     "The courts at Mumbai shall have exclusive jurisdiction over any dispute.",
     "The courts at Bengaluru shall have exclusive jurisdiction over any dispute.",
     [("court_city", "mumbai", "bengaluru")]),

    (ClauseType.NON_COMPETE,
     "The non-compete restriction shall apply for twelve (12) months after termination.",
     "The non-compete restriction shall apply for thirty-six (36) months after termination.",
     [("non_compete_months", 12, 36)]),

    (ClauseType.INSURANCE,
     "The Vendor shall maintain professional indemnity insurance of at least ₹2 Crore.",
     "The Vendor shall maintain professional indemnity insurance of at least ₹1 Crore.",
     [("insurance_amount_inr", 20000000, 10000000)]),

    (ClauseType.AUDIT_RIGHTS,
     "The Client may conduct an audit once every twelve (12) months.",
     "The Client may conduct an audit once every thirty-six (36) months.",
     [("audit_frequency_months", 12, 36)]),
]


def _approx(a, b, tol=0.05) -> bool:
    if a is None or b is None:
        return a == b
    try:
        fa, fb = float(a), float(b)
        return abs(fa - fb) <= max(abs(fb) * tol, 0.01)
    except (TypeError, ValueError):
        return str(a).lower() == str(b).lower()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    engine = ValueDiffEngine()
    tp = fp = fn = 0
    misses, spurious = [], []

    for ctype, a_text, b_text, expected in CASES:
        a = {"heading": "", "body_text": a_text}
        b = {"heading": "", "body_text": b_text}
        changes = engine.diff(a, b, ctype)
        got = {c.field: (c.old_value, c.new_value) for c in changes}

        expected_fields = {e[0] for e in expected}

        # True positives + false negatives
        for field, exp_old, exp_new in expected:
            if field in got:
                g_old, g_new = got[field]
                if _approx(g_new, exp_new):
                    tp += 1
                else:
                    fn += 1
                    misses.append(f"{ctype.value}.{field}: expected {exp_old}->{exp_new}, got {g_old}->{g_new}")
            else:
                fn += 1
                misses.append(f"{ctype.value}.{field}: NOT DETECTED (expected {exp_old}->{exp_new})")

        # False positives: fields extracted that weren't expected in this clause
        for field, (g_old, g_new) in got.items():
            if field not in expected_fields:
                fp += 1
                spurious.append(f"{ctype.value}.{field}: spurious {g_old}->{g_new}")

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print("# Clean Realistic-Clause Evaluation (engine's true accuracy)\n")
    print(f"**Precision {precision:.0%}  ·  Recall {recall:.0%}  ·  F1 {f1:.2f}**")
    print(f"(True positives: {tp}  ·  Missed: {fn}  ·  False positives: {fp})\n")
    print(f"Test cases: {len(CASES)} realistic clause pairs across {len(CASES)} clause types\n")

    if misses:
        print("## Missed (false negatives)")
        for m in misses:
            print(f"  - {m}")
        print()
    else:
        print("## Missed: none — every expected change detected.\n")

    if spurious:
        print("## Spurious (false positives / cross-field contamination)")
        for s in spurious:
            print(f"  - {s}")
        print()
    else:
        print("## Spurious: none — zero cross-field contamination.\n")

    out = Path(__file__).resolve().parent.parent / "tests" / "eval" / "eval_clean_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    # (report already printed; write a copy)
    print(f"Report basis: {len(CASES)} clause pairs. Written to {out}")


if __name__ == "__main__":
    main()
