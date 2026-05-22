"""
Agent 3: Indian Law Validator

Uses RAG: embeds each clause, retrieves relevant passages from the Indian law
corpus in Qdrant (shared collection), and asks Claude whether the clause
complies with the applicable law.

Relevant corpus: Indian Contract Act 1872, IT Act 2000, MSME Act 2006,
Maharashtra Shops and Establishments Act, and related Maharashtra laws.

Runs up to 5 Claude calls concurrently (asyncio.gather) so a 50-clause
contract finishes in ~2-4 minutes rather than serially.
"""

import asyncio
import json
from typing import Any

from app.agents.base_agent import PROMPT_VERSION, BaseAgent
from app.core.config import settings
from app.core.constants import FindingSeverity
from app.integrations.anthropic_client import call_claude
from app.integrations import qdrant_client
from app.integrations.voyage_client import embed_query
from app.utils.text_utils import strip_json_fences

_SYSTEM_PROMPT = """\
You are a legal expert specialising in Indian contract law. You will be given a
contract clause and the most relevant excerpts from Indian statutes.

Determine whether the clause is compliant, potentially non-compliant, or
clearly non-compliant with the cited law.

Respond ONLY with valid JSON — no markdown, no prose outside the JSON:
{
  "compliance_status": "compliant" | "potentially_non_compliant" | "non_compliant",
  "applicable_law": "<Act name>",
  "section_reference": "<Section number, e.g. Section 23>",
  "explanation": "<brief explanation>",
  "recommendation": "<what to change, or null if compliant>"
}
"""

_CONCURRENT_LIMIT = 5  # max parallel Claude calls


async def _validate_one_clause(
    clause: dict,
    law_collection: str,
) -> dict | None:
    """
    Embed clause → RAG search → Claude call.
    Returns a finding dict or None if the clause is compliant / no law found.
    """
    text = clause.get("body_text", "").strip()
    if not text or len(text) < 50:
        return None

    query_vector = await embed_query(text)
    law_passages = await qdrant_client.search_vectors(
        collection_name=law_collection,
        query_vector=query_vector,
        top_k=5,
        score_threshold=0.65,
    )

    if not law_passages:
        return None

    law_context = "\n\n".join(
        f"[{p['payload'].get('act_name', p['payload'].get('source', 'Law'))} "
        f"{p['payload'].get('section_number', '')}]: "
        f"{p['payload'].get('text', '')}"
        for p in law_passages
    )

    prompt_content = (
        f"CONTRACT CLAUSE:\n{text[:4000]}\n\n"
        f"RELEVANT INDIAN LAW EXCERPTS:\n{law_context[:6000]}"
    )

    response_text, usage = await call_claude(
        messages=[{"role": "user", "content": prompt_content}],
        system=_SYSTEM_PROMPT,
        model=settings.ANTHROPIC_MODEL,
    )

    try:
        assessment = json.loads(strip_json_fences(response_text))
    except json.JSONDecodeError:
        return None

    if assessment.get("compliance_status") == "compliant":
        return {"_usage": usage}  # return usage only so caller can track tokens

    severity = (
        FindingSeverity.HIGH
        if assessment.get("compliance_status") == "non_compliant"
        else FindingSeverity.MEDIUM
    )

    # Best matching passage for citation
    best_passage = law_passages[0]
    payload = best_passage.get("payload", {})

    return {
        "_usage": usage,
        "_finding": {
            "flag_type": "law_violation",
            "severity": severity,
            "title": f"Potential law issue: {clause.get('heading') or 'Clause'}",
            "source_clause_id": clause.get("id"),
            "description": assessment.get("explanation", ""),
            "recommendation": assessment.get("recommendation"),
            "confidence": best_passage["score"],
            "reasoning_trace": (
                f"Applicable law: {assessment.get('applicable_law')} "
                f"{assessment.get('section_reference', '')}"
            ),
            "law_act_name": payload.get("act_name") or assessment.get("applicable_law"),
            "law_section_number": (
                payload.get("section_number") or assessment.get("section_reference")
            ),
            "law_retrieved_text": payload.get("text", "")[:1000],
            "law_jurisdiction": payload.get("jurisdiction", "india"),
        },
    }


class LawValidatorAgent(BaseAgent):
    name = "law_validator"

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        context keys:
          - project_id: str
          - tenant_id: str
          - clauses: list[dict]   (clauses from the document under review)
        """
        project_id = context["project_id"]
        tenant_id = context["tenant_id"]
        clauses = context["clauses"]

        self._log_run_start(project_id, tenant_id)

        law_collection = settings.QDRANT_LAW_COLLECTION
        total_tokens = {"input_tokens": 0, "output_tokens": 0}
        findings = []

        # Process in batches of _CONCURRENT_LIMIT to avoid rate-limiting
        semaphore = asyncio.Semaphore(_CONCURRENT_LIMIT)

        async def _bounded(clause: dict) -> dict | None:
            async with semaphore:
                return await _validate_one_clause(clause, law_collection)

        results = await asyncio.gather(
            *[_bounded(c) for c in clauses],
            return_exceptions=True,
        )

        for result in results:
            if result is None or isinstance(result, Exception):
                continue
            usage = result.get("_usage", {})
            total_tokens["input_tokens"] += usage.get("input_tokens", 0)
            total_tokens["output_tokens"] += usage.get("output_tokens", 0)
            finding_data = result.get("_finding")
            if finding_data:
                findings.append(self._build_finding(
                    flag_type=finding_data["flag_type"],
                    severity=finding_data["severity"],
                    title=finding_data["title"],
                    description=finding_data["description"],
                    recommendation=finding_data.get("recommendation"),
                    source_clause_id=finding_data.get("source_clause_id"),
                    confidence=finding_data.get("confidence"),
                    reasoning_trace=finding_data.get("reasoning_trace"),
                    law_act_name=finding_data.get("law_act_name"),
                    law_section_number=finding_data.get("law_section_number"),
                    law_retrieved_text=finding_data.get("law_retrieved_text"),
                    law_jurisdiction=finding_data.get("law_jurisdiction"),
                ))

        self._log_run_complete(project_id, len(findings))

        return {
            "findings": findings,
            "token_usage": total_tokens,
            "model_version": settings.ANTHROPIC_MODEL,
            "prompt_version": PROMPT_VERSION,
        }
