"""
Base class for all AI agents.

Every agent follows the same contract:
  - Receives a typed input dict
  - Calls Claude via anthropic_client
  - Returns a structured findings list + token usage
  - All agents are stateless; tenant/project context is passed in, not stored
"""

from abc import ABC, abstractmethod
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

PROMPT_VERSION = "v1.0"


class BaseAgent(ABC):
    name: str = "base_agent"

    @abstractmethod
    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the agent.

        Args:
            context: Agent-specific input (parsed clauses, file bytes, rules, etc.)

        Returns:
            {
                "findings": list[dict],   # structured clause flags
                "token_usage": dict,
                "model_version": str,
                "prompt_version": str,
            }
        """
        ...

    def _build_finding(
        self,
        flag_type: str,
        severity: str,
        title: str,
        description: str,
        recommendation: str | None = None,
        source_clause_id: str | None = None,
        confidence: float | None = None,
        reasoning_trace: str | None = None,
        risk_score: int | None = None,
        law_act_name: str | None = None,
        law_section_number: str | None = None,
        law_retrieved_text: str | None = None,
        law_jurisdiction: str | None = None,
        clause_type: str | None = None,
        value_changes: list | None = None,
        suggestion: dict | None = None,
        priority: str | None = None,
    ) -> dict:
        return {
            "flag_type": flag_type[:64],
            "severity": severity,
            "title": title[:500] if title else title,
            "description": description,
            "recommendation": recommendation,
            "source_clause_id": source_clause_id,
            "confidence": confidence,
            "reasoning_trace": reasoning_trace,
            "risk_score": risk_score,
            "law_act_name": law_act_name[:255] if law_act_name else law_act_name,
            "law_section_number": law_section_number[:64] if law_section_number else law_section_number,
            "law_retrieved_text": law_retrieved_text,
            "law_jurisdiction": law_jurisdiction[:64] if law_jurisdiction else law_jurisdiction,
            "clause_type": clause_type,
            "value_changes": value_changes or [],
            "suggestion": suggestion,
            "priority": priority,
        }

    def _log_run_start(self, project_id: str, tenant_id: str) -> None:
        logger.info(f"{self.name}_run_start", project_id=project_id, tenant_id=tenant_id)

    def _log_run_complete(self, project_id: str, findings_count: int) -> None:
        logger.info(f"{self.name}_run_complete", project_id=project_id, findings=findings_count)
