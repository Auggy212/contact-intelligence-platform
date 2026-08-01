"""
Ground-truth evaluation harness for the contract analysis engine.

Parses the Test_Contracts_new DOCX files, runs the real analysis agents
(no DB, no Celery, no API keys), matches actual findings against a
lawyer-style gold set, and reports precision / recall / F1 plus the exact
false positives and false negatives.

Run from backend/:
    python scripts/run_eval.py
    python scripts/run_eval.py --json          # also write eval_report.json
    python scripts/run_eval.py --contracts DIR  # override contracts dir

This is the "ruler" that turns "I think it works" into measurable accuracy.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Make `app` importable when run from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.parsers.normalizer import parse_document          # noqa: E402
from app.agents.template_comparison import TemplateComparisonAgent  # noqa: E402
from app.agents.vendor_diff import VendorDiffAgent          # noqa: E402
from app.agents.law_validator import LawValidatorAgent      # noqa: E402
from app.agents.checklist_validator import ChecklistValidatorAgent  # noqa: E402

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_SEV_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

# Default checklist rules (mirrors the 6 seeded defaults) so the eval runs
# without a database.
_DEFAULT_CHECKLIST_RULES = [
    {"rule_code": "A", "name": "Agreement Duration", "severity": "medium",
     "rule_config": {"min_months": 12, "max_months": 36}},
    {"rule_code": "B", "name": "Agreement Date", "severity": "low",
     "rule_config": {}},
    {"rule_code": "C", "name": "Dispute Court City", "severity": "high",
     "rule_config": {"allowed_cities": ["mumbai"]}},
    {"rule_code": "D", "name": "Advance Payment", "severity": "high",
     "rule_config": {"max_percent": 10}},
    {"rule_code": "E", "name": "Contract Value", "severity": "medium",
     "rule_config": {"max_value_inr": 7500000}},
    {"rule_code": "F", "name": "Termination Notice Period", "severity": "medium",
     "rule_config": {"min_months": 1, "max_months": 3}},
]


# ─────────────────────────────────────────────────────────────────────────────
# Parsing + running agents
# ─────────────────────────────────────────────────────────────────────────────

def _parse(path: Path) -> list[dict]:
    data = path.read_bytes()
    parsed = parse_document(data, path.name, _DOCX_MIME)
    clauses = []
    for i, c in enumerate(parsed["clauses"]):
        cc = dict(c)
        cc["id"] = f"{path.stem}-{i}"        # synthetic id for eval
        clauses.append(cc)
    return clauses


async def _run_agents(clauses_a, clauses_b, clauses_c) -> dict[str, list[dict]]:
    ctx_common = {"project_id": "eval", "tenant_id": "eval"}

    tc = await TemplateComparisonAgent().run(
        {**ctx_common, "clauses_a": clauses_a, "clauses_b": clauses_b}
    )
    vd = await VendorDiffAgent().run(
        {**ctx_common, "clauses_b": clauses_b, "clauses_c": clauses_c}
    )
    law = await LawValidatorAgent().run(
        {**ctx_common, "clauses": clauses_b}
    )
    full_text_b = "\n\n".join(c.get("body_text", "") for c in clauses_b)
    chk = await ChecklistValidatorAgent().run(
        {**ctx_common, "full_text": full_text_b, "rules": _DEFAULT_CHECKLIST_RULES}
    )

    return {
        "template_comparison": tc["findings"],
        "vendor_diff": vd["findings"],
        "law_validation": law["findings"],
        "checklist_validation": chk["findings"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Matching helpers — decide whether an actual finding satisfies an expected one
# ─────────────────────────────────────────────────────────────────────────────

def _finding_fields(f: dict) -> set[str]:
    """All value-change field names referenced by a finding."""
    fields = set()
    vcs = f.get("value_changes") or []
    for vc in vcs:
        if isinstance(vc, dict) and vc.get("field"):
            fields.add(vc["field"])
    # Also parse field= from reasoning_trace as a fallback
    rt = f.get("reasoning_trace") or ""
    for part in rt.split(";"):
        part = part.strip()
        if part.startswith("field="):
            fields.add(part.split("=", 1)[1].strip())
    return fields


def _finding_field_values(f: dict) -> dict[str, tuple]:
    """Map field -> (old_value, new_value) for a finding's value changes."""
    out = {}
    for vc in (f.get("value_changes") or []):
        if isinstance(vc, dict) and vc.get("field"):
            out[vc["field"]] = (vc.get("old_value"), vc.get("new_value"))
    return out


def _approx(a, b, tol=0.05) -> bool:
    """Loose numeric/categorical equality for matching gold values to actuals."""
    if a is None or b is None:
        return a == b
    try:
        fa, fb = float(a), float(b)
        if fb == 0:
            return abs(fa - fb) < 0.01
        return abs(fa - fb) / max(abs(fb), 1e-9) <= tol
    except (TypeError, ValueError):
        return str(a).lower() == str(b).lower()


def _match_value_change(expected: dict, findings: list[dict]) -> dict | None:
    """
    Find an actual finding that reports the expected field's change with the
    correct old→new values. Matching on VALUE (not just field name) so that a
    spurious extraction of the right field but wrong value does NOT count as a
    correct catch.
    """
    field = expected["field"]
    exp_old = expected.get("old")
    exp_new = expected.get("new")
    # First pass: field + value match
    for f in findings:
        fv = _finding_field_values(f)
        if field in fv:
            got_old, got_new = fv[field]
            if exp_old is None and exp_new is None:
                return f  # removal/categorical without explicit values
            if _approx(got_new, exp_new) and (exp_old is None or _approx(got_old, exp_old)):
                return f
    # Second pass (removals): field present with new=None
    if exp_old is None and exp_new is None:
        for f in findings:
            if field in _finding_fields(f):
                return f
    return None


def _match_keyword(expected: dict, findings: list[dict]) -> dict | None:
    kw = (expected.get("keyword") or "").lower()
    for f in findings:
        hay = f"{f.get('title','')} {f.get('description','')} {f.get('law_act_name','')}".lower()
        if kw in hay:
            return f
    return None


def _match_concept(expected: dict, findings: list[dict]) -> dict | None:
    kw = (expected.get("concept") or "").lower()
    for f in findings:
        title = (f.get("title") or "").lower()
        desc = (f.get("description") or "").lower()
        # concept findings carry the concept name in the title
        if kw in title or kw in desc:
            return f
    return None


def _severity_ok(finding: dict, min_severity: str) -> bool:
    if not min_severity:
        return True
    return _SEV_RANK.get(finding.get("severity", "low"), 0) >= _SEV_RANK.get(min_severity, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation per section
# ─────────────────────────────────────────────────────────────────────────────

def _eval_expected_list(
    expected_items: list[dict],
    findings: list[dict],
    match_fn,
    key_field: str,
) -> tuple[list[dict], list[dict], set[int]]:
    """
    Returns (hits, misses, matched_finding_indices).
      hits   = expected items that were found (true positives)
      misses = expected items not found (false negatives)
    """
    hits, misses = [], []
    matched_idx: set[int] = set()
    for exp in expected_items:
        found = match_fn(exp, findings)
        if found is not None and _severity_ok(found, exp.get("min_severity", "")):
            hits.append({"expected": exp, "matched_title": found.get("title", "")[:80]})
            # record which finding matched (by identity)
            for i, f in enumerate(findings):
                if f is found:
                    matched_idx.add(i)
                    break
        else:
            misses.append({"expected": exp})
    return hits, misses, matched_idx


def evaluate() -> dict:
    root = Path(__file__).resolve().parent.parent
    gold_path = root / "tests" / "eval" / "gold_set.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))

    contracts_dir = _CONTRACTS_DIR
    files = gold["contracts"]
    clauses_a = _parse(contracts_dir / files["template"])
    clauses_b = _parse(contracts_dir / files["proposed"])
    clauses_c = _parse(contracts_dir / files["vendor_reply"])

    findings = asyncio.run(_run_agents(clauses_a, clauses_b, clauses_c))

    report: dict = {"sections": {}, "totals": {}}

    # ── Template comparison ──────────────────────────────────────────────────
    tc_findings = findings["template_comparison"]
    tc_gold = gold["template_comparison"]

    vc_hits, vc_miss, vc_idx = _eval_expected_list(
        tc_gold["value_changes"], tc_findings, _match_value_change, "field")
    vr_hits, vr_miss, vr_idx = _eval_expected_list(
        tc_gold["value_removals"], tc_findings, _match_value_change, "field")
    cat_hits, cat_miss, cat_idx = _eval_expected_list(
        tc_gold["categorical_changes"], tc_findings, _match_value_change, "field")
    con_hits, con_miss, con_idx = _eval_expected_list(
        tc_gold["concepts"], tc_findings, _match_concept, "concept")

    tc_expected = (tc_gold["value_changes"] + tc_gold["value_removals"]
                   + tc_gold["categorical_changes"] + tc_gold["concepts"])
    tc_hits = vc_hits + vr_hits + cat_hits + con_hits
    tc_miss = vc_miss + vr_miss + cat_miss + con_miss

    report["sections"]["template_comparison"] = _section_report(
        "Template Comparison (A vs B)", tc_expected, tc_hits, tc_miss, tc_findings)

    # ── Vendor diff ──────────────────────────────────────────────────────────
    vd_findings = findings["vendor_diff"]
    vd_gold = gold["vendor_diff"]
    vdvc_hits, vdvc_miss, _ = _eval_expected_list(
        vd_gold["value_changes"], vd_findings, _match_value_change, "field")
    vdnc_hits, vdnc_miss, _ = _eval_expected_list(
        vd_gold["new_clauses"], vd_findings, _match_keyword, "keyword")
    vd_expected = vd_gold["value_changes"] + vd_gold["new_clauses"]
    vd_hits = vdvc_hits + vdnc_hits
    vd_miss = vdvc_miss + vdnc_miss
    report["sections"]["vendor_diff"] = _section_report(
        "Vendor Diff (B vs C)", vd_expected, vd_hits, vd_miss, vd_findings)

    # ── Law validation ───────────────────────────────────────────────────────
    law_findings = findings["law_validation"]
    law_gold = gold["law_validation"]["rules"]
    law_hits, law_miss, _ = _eval_expected_list(
        law_gold, law_findings, _match_keyword, "keyword")
    report["sections"]["law_validation"] = _section_report(
        "Law Validation (B)", law_gold, law_hits, law_miss, law_findings)

    # ── Checklist ────────────────────────────────────────────────────────────
    chk_findings = findings["checklist_validation"]
    chk_gold = gold["checklist_validation"]["rules"]
    chk_hits, chk_miss, _ = _eval_expected_list(
        chk_gold, chk_findings, _match_keyword, "keyword")
    report["sections"]["checklist_validation"] = _section_report(
        "Checklist Validation (B)", chk_gold, chk_hits, chk_miss, chk_findings)

    # ── Cross-field false-positive probe (the point-2 metric) ────────────────
    # Count value-change findings whose field is NOT in ANY gold expectation for
    # that section — these are spurious cross-field extractions.
    report["cross_field"] = _cross_field_probe(gold, findings)

    # ── Overall totals ───────────────────────────────────────────────────────
    tp = sum(s["true_positives"] for s in report["sections"].values())
    fn = sum(s["false_negatives"] for s in report["sections"].values())
    # False positives = spurious cross-field extractions (the point-2 metric)
    fp = sum(cf["spurious_field_count"] for cf in report["cross_field"].values())
    report["totals"] = _prf(tp, fp, fn)
    report["totals"]["true_positives"] = tp
    report["totals"]["false_negatives"] = fn
    report["totals"]["false_positives"] = fp

    return report


def _cross_field_probe(gold: dict, findings: dict) -> dict:
    """
    Detect spurious cross-field extractions: value-change findings whose field
    is not part of any gold-expected change for that section. High counts here
    = the false-positive problem we're targeting.
    """
    def gold_value_map(section: str) -> dict[str, list]:
        """field -> list of acceptable new-values from the gold set."""
        g = gold.get(section, {})
        m: dict[str, list] = {}
        for key in ("value_changes", "value_removals", "categorical_changes"):
            for item in g.get(key, []):
                fld = item.get("field")
                if fld:
                    m.setdefault(fld, []).append(item.get("new"))
        return m

    results = {}
    for section in ("template_comparison", "vendor_diff"):
        gmap = gold_value_map(section)
        spurious = []
        for f in findings[section]:
            for field, (_old, new) in _finding_field_values(f).items():
                if field not in gmap:
                    # field never expected in this section at all
                    spurious.append({"field": field, "new": new, "title": (f.get("title") or "")[:70]})
                else:
                    # field expected, but does this value match ANY gold value?
                    acceptable = gmap[field]
                    if all(g_new is not None and not _approx(new, g_new) for g_new in acceptable):
                        spurious.append({"field": field, "new": new, "title": (f.get("title") or "")[:70]})
        results[section] = {
            "spurious_field_count": len(spurious),
            "spurious_fields": spurious,
        }
    return results


def _prf(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


def _section_report(name, expected, hits, misses, findings) -> dict:
    """
    For a section, false positives are counted at the cross-field probe level,
    so per-section FP here is 0 by construction (we measure recall of the gold
    set per section, and FP globally via the cross-field probe). We still surface
    FP=spurious count for the sections that have field-based findings.
    """
    tp = len(hits)
    fn = len(misses)
    fp = 0  # section-level; cross-field FPs reported separately
    prf = _prf(tp, fp, fn)
    return {
        "name": name,
        "expected_count": len(expected),
        "true_positives": tp,
        "false_negatives": fn,
        "false_positives": fp,
        "precision": prf["precision"],
        "recall": prf["recall"],
        "f1": prf["f1"],
        "misses": [m["expected"] for m in misses],
        "actual_finding_count": len(findings),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────

def render_markdown(report: dict) -> str:
    lines = []
    lines.append("# Contract Engine — Ground-Truth Evaluation Report\n")
    t = report["totals"]
    lines.append(f"**Overall:  Recall {t['recall']:.0%}  ·  Precision {t['precision']:.0%}  ·  F1 {t['f1']:.2f}**")
    lines.append(f"(True positives: {t['true_positives']}  ·  Missed: {t['false_negatives']}  ·  Cross-field false positives tracked below)\n")

    lines.append("| Section | Expected | Caught | Missed | Recall |")
    lines.append("|---|---|---|---|---|")
    for s in report["sections"].values():
        lines.append(
            f"| {s['name']} | {s['expected_count']} | {s['true_positives']} "
            f"| {s['false_negatives']} | {s['recall']:.0%} |"
        )
    lines.append("")

    # Misses (false negatives)
    lines.append("## Missed expectations (false negatives)\n")
    any_miss = False
    for s in report["sections"].values():
        if s["misses"]:
            any_miss = True
            lines.append(f"**{s['name']}**")
            for m in s["misses"]:
                key = m.get("field") or m.get("concept") or m.get("keyword")
                lines.append(f"  - {key}")
            lines.append("")
    if not any_miss:
        lines.append("_None — every expected finding was caught._\n")

    # Cross-field false positives
    lines.append("## Cross-field false positives (the point-2 metric)\n")
    lines.append("Value-change findings whose field is not a genuine expected change — spurious extractions.\n")
    total_spurious = 0
    for section, data in report["cross_field"].items():
        cnt = data["spurious_field_count"]
        total_spurious += cnt
        lines.append(f"**{section}: {cnt} spurious field(s)**")
        for sp in data["spurious_fields"]:
            lines.append(f"  - `{sp['field']}` in: {sp['title']}")
        lines.append("")
    lines.append(f"**Total spurious cross-field extractions: {total_spurious}**\n")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────────────────────────────────────

_CONTRACTS_DIR = Path("C:/Users/Tanishk/Documents/Contract_Intelligence_platform/Test_Contracts_new")


def main() -> None:
    global _CONTRACTS_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="also write eval_report.json")
    ap.add_argument("--contracts", type=str, default=None, help="override contracts dir")
    args = ap.parse_args()

    if args.contracts:
        _CONTRACTS_DIR = Path(args.contracts)

    report = evaluate()
    md = render_markdown(report)

    # Print to console (utf-8 safe)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(md)

    out_dir = Path(__file__).resolve().parent.parent / "tests" / "eval"
    (out_dir / "eval_report.md").write_text(md, encoding="utf-8")
    if args.json:
        (out_dir / "eval_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport written to {out_dir / 'eval_report.md'}")


if __name__ == "__main__":
    main()
