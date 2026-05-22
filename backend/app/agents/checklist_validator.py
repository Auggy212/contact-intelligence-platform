"""
Agent 4: Checklist Validator

Two-phase validation:
1. LLM extraction: Claude extracts structured values (dates, durations, amounts, courts)
2. Python rules engine: deterministically validates each extracted value against
   per-tenant ChecklistRule configs. No LLM in the validation step itself.

If a value cannot be extracted, the result is "not_found" — NOT a "fail".
"""

import json
from datetime import date, datetime
from typing import Any

from app.agents.base_agent import PROMPT_VERSION, BaseAgent
from app.core.config import settings
from app.core.constants import FindingSeverity
from app.integrations.anthropic_client import call_claude
from app.utils.text_utils import strip_json_fences

_EXTRACTION_SYSTEM = """\
You are a contract data extractor. From the given contract text, extract the
following values. If a value is not found or unclear, set it to null.

Return ONLY valid JSON with these keys:
{
  "agreement_duration_months": number | null,
  "agreement_date": "YYYY-MM-DD" | null,
  "dispute_court_city": "string" | null,
  "advance_payment_percent": number | null,
  "contract_value_inr": number | null,
  "termination_notice_months": number | null
}
"""


def _fail(code: str, name: str, severity: str, detail: str, value: Any = None) -> dict:
    entry: dict = {"rule_code": code, "name": name, "result": "fail", "severity": severity, "detail": detail}
    if value is not None:
        entry["value"] = value
    return entry


def _not_found(code: str, name: str, severity: str) -> dict:
    return {"rule_code": code, "name": name, "result": "not_found", "severity": severity}


# ---------------------------------------------------------------------------
# Built-in rule validators (rule_code A-F, legacy — kept for backward compat)
# ---------------------------------------------------------------------------

def _validate_builtin(code: str, cfg: dict, name: str, severity: str,
                       extracted: dict, today: date) -> list[dict]:
    if code == "A":
        val = extracted.get("agreement_duration_months")
        if val is None:
            return [_not_found(code, name, severity)]
        if not (cfg.get("min_months", 12) <= val <= cfg.get("max_months", 36)):
            return [_fail(code, name, severity,
                          f"Duration {val}mo outside {cfg.get('min_months')}–{cfg.get('max_months')}mo", val)]
        return []

    if code == "B":
        val_str = extracted.get("agreement_date")
        if val_str is None:
            return [_not_found(code, name, severity)]
        try:
            val_date = datetime.strptime(val_str, "%Y-%m-%d").date()
            if val_date <= today:
                return [_fail(code, name, severity, f"Agreement date {val_str} is not a future date", val_str)]
        except ValueError:
            return [_not_found(code, name, severity)]
        return []

    if code == "C":
        val = extracted.get("dispute_court_city")
        allowed = [c.lower() for c in cfg.get("allowed_cities", ["mumbai"])]
        if val is None:
            return [_not_found(code, name, severity)]
        if val.lower() not in allowed:
            return [_fail(code, name, severity, f"Court city '{val}' not in allowed: {allowed}", val)]
        return []

    if code == "D":
        val = extracted.get("advance_payment_percent")
        max_pct = cfg.get("max_percent", 10)
        if val is None:
            return [_not_found(code, name, severity)]
        if val > max_pct:
            return [_fail(code, name, severity, f"Advance {val}% exceeds max {max_pct}%", val)]
        return []

    if code == "E":
        val = extracted.get("contract_value_inr")
        max_val = cfg.get("max_value_inr", 5_000_000)
        if val is None:
            return [_not_found(code, name, severity)]
        if val >= max_val:
            return [_fail(code, name, severity,
                          f"Contract value ₹{val:,} meets or exceeds ₹{max_val:,}", val)]
        return []

    if code == "F":
        val = extracted.get("termination_notice_months")
        if val is None:
            return [_not_found(code, name, severity)]
        if not (cfg.get("min_months", 1) <= val <= cfg.get("max_months", 3)):
            return [_fail(code, name, severity,
                          f"Notice {val}mo outside {cfg.get('min_months')}–{cfg.get('max_months')}mo", val)]
        return []

    return []  # unknown built-in code — skip


# ---------------------------------------------------------------------------
# Generic rule type validators for custom rules
# ---------------------------------------------------------------------------
# Supported rule_config["type"] values and their required config keys:
#
#   numeric_range   — {"type": "numeric_range", "field": str, "min": num, "max": num}
#                     Checks extracted[field] is within [min, max].
#
#   max_value       — {"type": "max_value", "field": str, "max": num}
#                     Checks extracted[field] <= max.
#
#   min_value       — {"type": "min_value", "field": str, "min": num}
#                     Checks extracted[field] >= min.
#
#   string_allowlist — {"type": "string_allowlist", "field": str, "allowed_values": [str, ...]}
#                      Checks extracted[field].lower() in allowed_values (case-insensitive).
#
#   date_future     — {"type": "date_future", "field": str}
#                     Checks the extracted date string (YYYY-MM-DD) is in the future.
#
#   date_past       — {"type": "date_past", "field": str}
#                     Checks the extracted date string (YYYY-MM-DD) is in the past.
#
#   boolean_present — {"type": "boolean_present", "field": str}
#                     Checks extracted[field] is not None (field must be present).

def _validate_custom(code: str, cfg: dict, name: str, severity: str,
                     extracted: dict, today: date) -> list[dict]:
    rule_type = cfg.get("type", "")
    field = cfg.get("field")

    if not field:
        # Misconfigured rule — treat as not_found so it surfaces for admin review
        return [_not_found(code, name, severity)]

    val = extracted.get(field)

    if rule_type == "numeric_range":
        low, high = cfg.get("min"), cfg.get("max")
        if val is None:
            return [_not_found(code, name, severity)]
        if low is not None and val < low:
            return [_fail(code, name, severity, f"{field} value {val} is below minimum {low}", val)]
        if high is not None and val > high:
            return [_fail(code, name, severity, f"{field} value {val} exceeds maximum {high}", val)]
        return []

    if rule_type == "max_value":
        max_v = cfg.get("max")
        if val is None:
            return [_not_found(code, name, severity)]
        if max_v is not None and val > max_v:
            return [_fail(code, name, severity, f"{field} value {val} exceeds maximum {max_v}", val)]
        return []

    if rule_type == "min_value":
        min_v = cfg.get("min")
        if val is None:
            return [_not_found(code, name, severity)]
        if min_v is not None and val < min_v:
            return [_fail(code, name, severity, f"{field} value {val} is below minimum {min_v}", val)]
        return []

    if rule_type == "string_allowlist":
        allowed = [v.lower() for v in cfg.get("allowed_values", [])]
        if val is None:
            return [_not_found(code, name, severity)]
        if str(val).lower() not in allowed:
            return [_fail(code, name, severity,
                          f"{field} value '{val}' not in allowed list: {cfg.get('allowed_values', [])}", val)]
        return []

    if rule_type == "date_future":
        if val is None:
            return [_not_found(code, name, severity)]
        try:
            val_date = datetime.strptime(str(val), "%Y-%m-%d").date()
            if val_date <= today:
                return [_fail(code, name, severity, f"{field} date {val} is not a future date", val)]
        except ValueError:
            return [_not_found(code, name, severity)]
        return []

    if rule_type == "date_past":
        if val is None:
            return [_not_found(code, name, severity)]
        try:
            val_date = datetime.strptime(str(val), "%Y-%m-%d").date()
            if val_date >= today:
                return [_fail(code, name, severity, f"{field} date {val} is not in the past", val)]
        except ValueError:
            return [_not_found(code, name, severity)]
        return []

    if rule_type == "boolean_present":
        if val is None:
            return [_fail(code, name, severity, f"Required field '{field}' was not found in the contract")]
        return []

    # Unknown type — surface as not_found rather than silently swallowing it
    return [_not_found(code, name, severity)]


_BUILTIN_CODES = {"A", "B", "C", "D", "E", "F"}


def _validate_rules(extracted: dict, rules: list[dict]) -> list[dict]:
    """
    Deterministic Python validation of extracted values against rule configs.
    Returns list of rule failure dicts.

    Built-in rules (A-F) are validated by code. Custom rules are dispatched
    by rule_config["type"] so new rules work without code changes.
    """
    today = date.today()
    failures = []

    for rule in rules:
        code = rule["rule_code"]
        cfg = rule["rule_config"]
        severity = rule["severity"]
        name = rule["name"]

        if code in _BUILTIN_CODES:
            failures.extend(_validate_builtin(code, cfg, name, severity, extracted, today))
        else:
            failures.extend(_validate_custom(code, cfg, name, severity, extracted, today))

    return failures


class ChecklistValidatorAgent(BaseAgent):
    name = "checklist_validator"

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        context keys:
          - project_id: str
          - tenant_id: str
          - full_text: str          (full contract text)
          - rules: list[dict]       (enabled ChecklistRule records serialized to dict)
        """
        project_id = context["project_id"]
        tenant_id = context["tenant_id"]
        full_text = context["full_text"]
        rules = context["rules"]

        self._log_run_start(project_id, tenant_id)

        # Phase 1: LLM extraction
        response_text, usage = await call_claude(
            messages=[{"role": "user", "content": f"CONTRACT TEXT:\n\n{full_text[:12000]}"}],
            system=_EXTRACTION_SYSTEM,
            model=settings.ANTHROPIC_MODEL,
        )

        try:
            extracted = json.loads(strip_json_fences(response_text))
        except json.JSONDecodeError:
            extracted = {}

        # Phase 2: Deterministic Python rules engine
        failures = _validate_rules(extracted, rules)

        severity_map = {
            "critical": FindingSeverity.CRITICAL,
            "high": FindingSeverity.HIGH,
            "medium": FindingSeverity.MEDIUM,
            "low": FindingSeverity.LOW,
        }

        findings = []
        for failure in failures:
            severity = severity_map.get(failure["severity"].lower(), FindingSeverity.MEDIUM)
            result = failure["result"]
            title = (
                f"Rule {failure['rule_code']} — {failure['name']}: "
                + ("Not extractable" if result == "not_found" else "FAILED")
            )
            findings.append(self._build_finding(
                flag_type="checklist_violation",
                severity=severity if result == "fail" else FindingSeverity.INFO,
                title=title,
                description=failure.get("detail", f"Value not found for rule {failure['rule_code']}"),
                recommendation=f"Review the {failure['name']} clause and ensure compliance.",
                confidence=0.95 if result == "fail" else 0.5,
                reasoning_trace=f"Extracted: {extracted}",
            ))

        self._log_run_complete(project_id, len(findings))

        return {
            "findings": findings,
            "extracted_values": extracted,
            "token_usage": usage,
            "model_version": settings.ANTHROPIC_MODEL,
            "prompt_version": PROMPT_VERSION,
        }
