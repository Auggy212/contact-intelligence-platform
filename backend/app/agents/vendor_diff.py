"""
Agent 2: Vendor Diff Analyser

Analyses the Vendor Reply document (C) against the Proposed Draft (B).
Leverages tracked insertions, tracked deletions, and strikethroughs parsed
from the OOXML to surface vendor redlines that carry legal risk.
"""

import json
from typing import Any

from app.agents.base_agent import PROMPT_VERSION, BaseAgent
from app.core.config import settings
from app.core.constants import FindingSeverity
from app.integrations.anthropic_client import call_claude
from app.utils.text_utils import strip_json_fences

_SYSTEM_PROMPT = """\
You are a contract risk specialist. You will receive a clause from a proposed
draft (B) and the vendor's redlined version of that clause from document (C),
including tracked insertions, deletions, and strikethroughs.

Evaluate the legal risk of the vendor's changes. Respond ONLY with valid JSON:
{
  "risk_level": "critical" | "high" | "medium" | "low",
  "risk_score": <integer 1-10, where 1=minimal risk and 10=maximum risk>,
  "risk_summary": "...",
  "specific_concerns": ["...", "..."],
  "recommendation": "..."
}
"""


def _format_redline(clause: dict) -> str:
    parts = [f"Text: {clause['body_text']}"]
    meta = clause.get("change_metadata", {})
    if clause.get("has_tracked_insertion"):
        parts.append(f"INSERTED text: {meta.get('insertions', [])}")
    if clause.get("has_tracked_deletion"):
        parts.append(f"DELETED text: {meta.get('deletions', [])}")
    if clause.get("has_strikethrough"):
        parts.append("Contains strikethrough formatting")
    return "\n".join(parts)


class VendorDiffAgent(BaseAgent):
    name = "vendor_diff"

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        context keys:
          - project_id: str
          - tenant_id: str
          - clauses_b: list[dict]   (proposed draft)
          - clauses_c: list[dict]   (vendor reply with OOXML change metadata)
        """
        project_id = context["project_id"]
        tenant_id = context["tenant_id"]
        clauses_b = context["clauses_b"]
        clauses_c = context["clauses_c"]

        self._log_run_start(project_id, tenant_id)

        findings = []
        total_tokens = {"input_tokens": 0, "output_tokens": 0}

        # Only analyse clauses in C that contain vendor redlines
        redlined_clauses = [
            c for c in clauses_c
            if c.get("has_tracked_insertion")
            or c.get("has_tracked_deletion")
            or c.get("has_strikethrough")
        ]

        for clause_c in redlined_clauses:
            # Find the corresponding clause in B by paragraph index
            matching_b = next(
                (c for c in clauses_b if c["paragraph_index"] == clause_c["paragraph_index"]),
                None,
            )

            prompt_content = (
                f"PROPOSED DRAFT CLAUSE (B):\n{matching_b['body_text'] if matching_b else 'Not found'}\n\n"
                f"VENDOR REDLINED CLAUSE (C):\n{_format_redline(clause_c)}"
            )

            response_text, usage = await call_claude(
                messages=[{"role": "user", "content": prompt_content}],
                system=_SYSTEM_PROMPT,
                model=settings.ANTHROPIC_MODEL,
            )
            total_tokens["input_tokens"] += usage["input_tokens"]
            total_tokens["output_tokens"] += usage["output_tokens"]

            try:
                assessment = json.loads(strip_json_fences(response_text))
            except json.JSONDecodeError:
                assessment = {"risk_level": "medium", "risk_score": 5, "risk_summary": response_text,
                              "specific_concerns": [], "recommendation": None}

            severity_map = {
                "critical": FindingSeverity.CRITICAL,
                "high": FindingSeverity.HIGH,
                "medium": FindingSeverity.MEDIUM,
                "low": FindingSeverity.LOW,
            }
            severity = severity_map.get(assessment.get("risk_level", "medium"), FindingSeverity.MEDIUM)

            raw_score = assessment.get("risk_score")
            risk_score = max(1, min(10, int(raw_score))) if raw_score is not None else None

            findings.append(self._build_finding(
                flag_type="vendor_redline",
                severity=severity,
                title=f"Vendor redline: {clause_c.get('heading') or 'Clause ' + str(clause_c['paragraph_index'])}",
                description=assessment.get("risk_summary", ""),
                recommendation=assessment.get("recommendation"),
                source_clause_id=clause_c.get("id"),
                confidence=0.9,
                reasoning_trace=str(assessment.get("specific_concerns", [])),
                risk_score=risk_score,
            ))

        self._log_run_complete(project_id, len(findings))

        return {
            "findings": findings,
            "token_usage": total_tokens,
            "model_version": settings.ANTHROPIC_MODEL,
            "prompt_version": PROMPT_VERSION,
        }
