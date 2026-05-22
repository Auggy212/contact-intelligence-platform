"""
Agent 1: Template Comparison Agent

Compares the Master Template (A) against the Proposed Draft (B) using
cosine similarity on voyage-law-2 embeddings. Flags clauses in B that
are missing, significantly altered, or added relative to A.
"""

import json
from typing import Any

import numpy as np

from app.agents.base_agent import PROMPT_VERSION, BaseAgent
from app.core.config import settings
from app.core.constants import FindingSeverity
from app.integrations.anthropic_client import call_claude
from app.integrations.voyage_client import embed_texts
from app.utils.text_utils import strip_json_fences

_SIMILARITY_THRESHOLD = 0.85  # Below this → clause is flagged as significantly altered
_SYSTEM_PROMPT = """\
You are a contract review expert. You will be given pairs of clauses from a
master template (A) and a proposed draft (B). For each pair, assess whether
the proposed draft clause materially differs from the master template.
Respond in JSON with this structure:
{
  "assessment": "altered" | "acceptable" | "missing",
  "risk_level": "critical" | "high" | "medium" | "low",
  "explanation": "...",
  "recommendation": "..."
}
"""


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    a, b = np.array(vec_a), np.array(vec_b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


class TemplateComparisonAgent(BaseAgent):
    name = "template_comparison"

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        context keys:
          - project_id: str
          - tenant_id: str
          - clauses_a: list[dict]   (parsed clauses from template A)
          - clauses_b: list[dict]   (parsed clauses from proposed draft B)
        """
        project_id = context["project_id"]
        tenant_id = context["tenant_id"]
        clauses_a = context["clauses_a"]
        clauses_b = context["clauses_b"]

        self._log_run_start(project_id, tenant_id)

        texts_a = [c["body_text"] for c in clauses_a]
        texts_b = [c["body_text"] for c in clauses_b]

        embeds_a = await embed_texts(texts_a)
        embeds_b = await embed_texts(texts_b)

        findings = []
        total_tokens = {"input_tokens": 0, "output_tokens": 0}

        # For each clause in B, find best matching clause in A
        for idx_b, (clause_b, emb_b) in enumerate(zip(clauses_b, embeds_b)):
            if not texts_b[idx_b].strip():
                continue

            similarities = [_cosine_similarity(emb_b, emb_a) for emb_a in embeds_a]
            best_score = max(similarities) if similarities else 0.0
            best_idx_a = similarities.index(best_score) if similarities else -1

            if best_score < _SIMILARITY_THRESHOLD and best_idx_a >= 0:
                clause_a = clauses_a[best_idx_a]
                # Ask Claude for a qualitative assessment of the pair
                messages = [{
                    "role": "user",
                    "content": (
                        f"TEMPLATE CLAUSE (A):\n{clause_a['body_text']}\n\n"
                        f"PROPOSED DRAFT CLAUSE (B):\n{clause_b['body_text']}\n\n"
                        f"Cosine similarity: {best_score:.3f}"
                    ),
                }]
                response_text, usage = await call_claude(
                    messages=messages,
                    system=_SYSTEM_PROMPT,
                    model=settings.ANTHROPIC_MODEL,
                )
                total_tokens["input_tokens"] += usage["input_tokens"]
                total_tokens["output_tokens"] += usage["output_tokens"]

                try:
                    assessment = json.loads(strip_json_fences(response_text))
                except json.JSONDecodeError:
                    assessment = {"assessment": "altered", "risk_level": "medium",
                                  "explanation": response_text, "recommendation": None}

                severity_map = {
                    "critical": FindingSeverity.CRITICAL,
                    "high": FindingSeverity.HIGH,
                    "medium": FindingSeverity.MEDIUM,
                    "low": FindingSeverity.LOW,
                }
                severity = severity_map.get(assessment.get("risk_level", "medium"), FindingSeverity.MEDIUM)

                # Derive numeric risk score from cosine similarity: lower similarity = higher risk
                # similarity 0.0 → score 10, similarity 0.85 → score 1
                risk_score = max(1, min(10, round(10 - (best_score / 0.85) * 9)))

                findings.append(self._build_finding(
                    flag_type="template_deviation",
                    severity=severity,
                    title=f"Clause altered vs. template: {clause_b.get('heading') or 'Untitled'}",
                    description=assessment.get("explanation", ""),
                    recommendation=assessment.get("recommendation"),
                    source_clause_id=clause_b.get("id"),
                    confidence=round(best_score, 4),
                    reasoning_trace=f"Similarity={best_score:.3f}. Assessment={assessment.get('assessment')}",
                    risk_score=risk_score,
                ))

        self._log_run_complete(project_id, len(findings))

        return {
            "findings": findings,
            "token_usage": total_tokens,
            "model_version": settings.ANTHROPIC_MODEL,
            "prompt_version": PROMPT_VERSION,
        }
