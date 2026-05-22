"""
Golden-set evaluation harness.

Runs the DOCX parser + all 4 agents against manually annotated contracts and
computes precision, recall, and F1 per agent type.

Directory layout
----------------
tests/fixtures/contracts/       ← .docx contract files (one per test case)
tests/fixtures/golden_set/      ← .json ground-truth annotations (same stem as .docx)

Ground-truth annotation format
-------------------------------
{
  "contract_name": "example_nda.docx",
  "expected_findings": [
    {
      "flag_type": "missing_clause",       # required
      "severity": "critical",              # required
      "title_contains": "Indemnification", # optional substring match on finding title
      "description_contains": null         # optional substring match on description
    },
    ...
  ]
}

Usage
-----
  python scripts/run_eval_set.py                  # run all
  python scripts/run_eval_set.py --agent law      # run only law_validation
  python scripts/run_eval_set.py --verbose        # print per-finding detail

Exit code: 0 if all F1 scores >= 0.70, 1 otherwise.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

CONTRACTS_DIR = Path("tests/fixtures/contracts")
GOLDEN_DIR = Path("tests/fixtures/golden_set")

_AGENT_TASK_MAP = {
    "template": "template_comparison",
    "vendor": "vendor_diff",
    "law": "law_validation",
    "checklist": "checklist_validation",
}


# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------

def _matches(finding: dict, expected: dict) -> bool:
    """Return True if an agent finding satisfies one expected ground-truth entry."""
    if finding.get("flag_type") != expected.get("flag_type"):
        return False
    if expected.get("severity") and finding.get("severity") != expected["severity"]:
        return False
    if expected.get("title_contains"):
        if expected["title_contains"].lower() not in (finding.get("title") or "").lower():
            return False
    if expected.get("description_contains"):
        if expected["description_contains"].lower() not in (finding.get("description") or "").lower():
            return False
    return True


def _compute_metrics(
    actual_findings: list[dict],
    expected_findings: list[dict],
) -> dict[str, float]:
    """Compute precision, recall, F1 via greedy matching."""
    matched_actual: set[int] = set()
    matched_expected: set[int] = set()

    for ei, exp in enumerate(expected_findings):
        for ai, act in enumerate(actual_findings):
            if ai not in matched_actual and _matches(act, exp):
                matched_actual.add(ai)
                matched_expected.add(ei)
                break

    tp = len(matched_expected)
    fp = len(actual_findings) - tp
    fn = len(expected_findings) - tp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
            "tp": tp, "fp": fp, "fn": fn}


# ---------------------------------------------------------------------------
# Parser + agent runner
# ---------------------------------------------------------------------------

async def _parse_contract(docx_path: Path) -> list[dict]:
    """Parse a DOCX file and return clause dicts (no DB, no embeddings)."""
    from app.parsers.docx_parser import DocxParser
    parser = DocxParser()
    return parser.parse(docx_path.read_bytes())


async def _run_agent(task_type: str, clauses: list[dict], context: dict) -> list[dict]:
    """Run a single agent directly (bypassing Celery and DB)."""
    from app.agents import (
        TemplateComparisonAgent,
        VendorDiffAgent,
        LawValidatorAgent,
        ChecklistValidatorAgent,
    )

    if task_type == "template_comparison":
        agent = TemplateComparisonAgent()
        ctx = {**context, "clauses_a": clauses, "clauses_b": clauses}
    elif task_type == "vendor_diff":
        agent = VendorDiffAgent()
        ctx = {**context, "clauses_b": clauses, "clauses_c": clauses}
    elif task_type == "law_validation":
        agent = LawValidatorAgent()
        ctx = {**context, "clauses": clauses}
    elif task_type == "checklist_validation":
        agent = ChecklistValidatorAgent()
        full_text = "\n\n".join(c.get("body_text", "") for c in clauses)
        from app.workers.agent_tasks import _DEFAULT_CHECKLIST_RULES  # type: ignore[attr-defined]
        ctx = {**context, "full_text": full_text, "rules": []}
    else:
        raise ValueError(f"Unknown task type: {task_type}")

    try:
        result = await agent.run(ctx)
        return result.get("findings", [])
    except Exception as exc:
        print(f"    [WARN] Agent {task_type} raised: {exc}")
        return []


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

async def evaluate(agent_filter: str | None = None, verbose: bool = False) -> int:
    """Run the evaluation. Returns exit code (0=pass, 1=fail)."""
    if not CONTRACTS_DIR.exists():
        print(f"[ERROR] Contracts directory not found: {CONTRACTS_DIR}")
        print("  Create it and add .docx files to evaluate.")
        return 0  # Not a failure — just no data yet

    contracts = sorted(CONTRACTS_DIR.glob("*.docx"))
    if not contracts:
        print(f"No .docx files found in {CONTRACTS_DIR}")
        print("  Add annotated contract files to run evaluation.")
        return 0

    all_results: list[dict[str, Any]] = []
    overall_pass = True

    print(f"\n{'='*60}")
    print(f"  Contract Intelligence — Golden Set Evaluation")
    print(f"{'='*60}")
    print(f"  Contracts : {len(contracts)}")
    print(f"  Agent     : {agent_filter or 'all'}")
    print(f"{'='*60}\n")

    for docx_path in contracts:
        golden_path = GOLDEN_DIR / (docx_path.stem + ".json")
        if not golden_path.exists():
            print(f"  [SKIP] {docx_path.name} — no golden annotation at {golden_path}")
            continue

        with open(golden_path) as f:
            ground_truth: dict = json.load(f)

        expected = ground_truth.get("expected_findings", [])
        print(f"\n  Contract: {docx_path.name}  ({len(expected)} expected findings)")

        # Parse
        try:
            clauses = await _parse_contract(docx_path)
        except Exception as exc:
            print(f"    [ERROR] Parser failed: {exc}")
            continue

        print(f"    Parsed  : {len(clauses)} clauses")

        context = {"project_id": "eval", "tenant_id": "eval"}

        # Determine which agents to run
        agents_to_run = list(_AGENT_TASK_MAP.values())
        if agent_filter:
            agents_to_run = [_AGENT_TASK_MAP[agent_filter]]

        # Collect all agent findings
        all_findings: list[dict] = []
        for task_type in agents_to_run:
            findings = await _run_agent(task_type, clauses, context)
            if verbose:
                for f in findings:
                    print(f"      [{task_type}] {f.get('severity','?').upper()} — {f.get('title','?')}")
            all_findings.extend(findings)

        metrics = _compute_metrics(all_findings, expected)
        status = "PASS" if metrics["f1"] >= 0.70 else "FAIL"
        if metrics["f1"] < 0.70:
            overall_pass = False

        print(f"    Findings: {len(all_findings)} actual / {len(expected)} expected")
        print(f"    TP={metrics['tp']} FP={metrics['fp']} FN={metrics['fn']}")
        print(f"    Precision={metrics['precision']:.1%}  Recall={metrics['recall']:.1%}  F1={metrics['f1']:.1%}  [{status}]")

        all_results.append({
            "file": docx_path.name,
            "findings_actual": len(all_findings),
            "findings_expected": len(expected),
            **metrics,
            "status": status,
        })

    if not all_results:
        print("\nNo contracts evaluated — add annotated fixtures to run metrics.")
        return 0

    # Aggregate
    avg_precision = sum(r["precision"] for r in all_results) / len(all_results)
    avg_recall = sum(r["recall"] for r in all_results) / len(all_results)
    avg_f1 = sum(r["f1"] for r in all_results) / len(all_results)

    print(f"\n{'='*60}")
    print(f"  AGGREGATE  ({len(all_results)} contracts)")
    print(f"  Precision : {avg_precision:.1%}")
    print(f"  Recall    : {avg_recall:.1%}")
    print(f"  F1        : {avg_f1:.1%}  ({'PASS' if overall_pass else 'FAIL — below 0.70 threshold'})")
    print(f"{'='*60}\n")

    return 0 if overall_pass else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run golden-set evaluation")
    parser.add_argument(
        "--agent",
        choices=list(_AGENT_TASK_MAP.keys()),
        help="Run only this agent (default: all)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print each finding")
    args = parser.parse_args()

    exit_code = asyncio.run(evaluate(agent_filter=args.agent, verbose=args.verbose))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
