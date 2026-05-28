"""
Agent 4: Checklist Validator (demo mode — no API keys required)

Two-phase validation using pure Python:
1. Regex extraction: extracts dates, durations, amounts, courts from contract text
2. Python rules engine: deterministically validates each extracted value against
   per-tenant ChecklistRule configs.

Replaces the original Claude-based LLM extraction phase with deterministic regex.
"""

import re
from datetime import date, datetime
from typing import Any

from app.agents.base_agent import PROMPT_VERSION, BaseAgent
from app.core.constants import FindingSeverity
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Regex extractors for each supported field
# ---------------------------------------------------------------------------

_DATE_PATTERNS = [
    # DD/MM/YYYY or DD-MM-YYYY
    r"\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b",
    # YYYY-MM-DD
    r"\b(\d{4})-(\d{2})-(\d{2})\b",
    # "1st January 2025", "25 March 2026"
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b",
    # "January 25, 2025"
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b",
]

_MONTH_MAP = {m: i for i, m in enumerate(
    ["January","February","March","April","May","June",
     "July","August","September","October","November","December"], 1
)}

def _extract_dates(text: str) -> list[date]:
    results = []
    # YYYY-MM-DD
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        try:
            results.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            pass
    # DD/MM/YYYY
    for m in re.finditer(r"\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b", text):
        try:
            results.append(date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
        except ValueError:
            pass
    # 1st January 2025
    for m in re.finditer(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|"
        r"August|September|October|November|December)\s+(\d{4})\b", text, re.IGNORECASE
    ):
        try:
            results.append(date(int(m.group(3)), _MONTH_MAP[m.group(2).capitalize()], int(m.group(1))))
        except (ValueError, KeyError):
            pass
    # January 25, 2025
    for m in re.finditer(
        r"\b(January|February|March|April|May|June|July|August|September|October|"
        r"November|December)\s+(\d{1,2}),?\s+(\d{4})\b", text, re.IGNORECASE
    ):
        try:
            results.append(date(int(m.group(3)), _MONTH_MAP[m.group(1).capitalize()], int(m.group(2))))
        except (ValueError, KeyError):
            pass
    return results


def _extract_duration_months(text: str) -> float | None:
    """Extract contract duration expressed in months or years."""
    # "24 months", "2 years", "18-month term"
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*[\-\s]?month", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*[\-\s]?year", text, re.IGNORECASE)
    if m:
        return float(m.group(1)) * 12
    return None


def _extract_court_city(text: str) -> str | None:
    """Extract jurisdiction / court city from dispute resolution clause."""
    cities = [
        "mumbai", "delhi", "bangalore", "bengaluru", "hyderabad",
        "chennai", "kolkata", "pune", "ahmedabad", "surat", "jaipur",
        "lucknow", "nagpur",
    ]
    for city in cities:
        if re.search(r"\b" + city + r"\b", text, re.IGNORECASE):
            return city
    # Also check for "courts of <City>"
    m = re.search(r"\bcourts?\s+(?:of|at|in)\s+([A-Z][a-z]+)", text)
    if m:
        return m.group(1).lower()
    return None


def _extract_advance_payment_percent(text: str) -> float | None:
    """Extract advance payment percentage."""
    patterns = [
        r"\badvance\b.*?(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*(?:advance|upfront|mobilization)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


def _extract_contract_value_inr(text: str) -> float | None:
    """Extract contract value in INR (rupees)."""
    # "Rs. 50,00,000" / "INR 5000000" / "₹ 50 lakhs" / "50 crore"
    # Crore
    m = re.search(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)\s*crore", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "")) * 1e7
    # Lakh / Lac
    m = re.search(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)\s*la(?:kh|c)", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "")) * 1e5
    # Plain number with currency symbol
    m = re.search(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)\b", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def _extract_termination_notice_months(text: str) -> float | None:
    """Extract notice period for termination."""
    # "2 months prior written notice" / "2-month notice" / "notice of 2 months"
    # Try all common orderings
    patterns_months = [
        r"(?:notice|prior written notice|written notice)\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*[\-\s]?month",
        r"(\d+(?:\.\d+)?)\s*[\-\s]?month(?:s)?\s+(?:\w+\s+){0,3}notice",
        r"with\s+(\d+(?:\.\d+)?)\s*[\-\s]?month(?:s)?\s+(?:\w+\s+){0,2}notice",
        r"(?:termination|terminate)\s+.*?(\d+(?:\.\d+)?)\s*[\-\s]?month",
        r"(\d+(?:\.\d+)?)\s*[\-\s]?month(?:s)?\s+(?:written\s+)?notice",
    ]
    for p in patterns_months:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return float(m.group(1))
    # days → convert to months
    patterns_days = [
        r"(?:notice|prior.*?notice|written notice)\s+(?:of\s+)?(\d+)\s*[\-\s]?day",
        r"(\d+)\s*[\-\s]?day(?:s)?\s+(?:\w+\s+){0,2}notice",
        r"with\s+(\d+)\s*[\-\s]?day(?:s)?\s+(?:\w+\s+){0,2}notice",
    ]
    for p in patterns_days:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return round(float(m.group(1)) / 30, 2)
    return None


def _extract_all_fields(full_text: str) -> dict:
    """Run all extractors over the full contract text and return a flat dict."""
    dates = _extract_dates(full_text)
    today = date.today()

    # Pick the most likely "agreement date" — first date that is on or before today
    agreement_date = None
    for d in sorted(dates):
        if d <= today:
            agreement_date = d.isoformat()
            break

    return {
        "agreement_duration_months": _extract_duration_months(full_text),
        "agreement_date": agreement_date,
        "dispute_court_city": _extract_court_city(full_text),
        "advance_payment_percent": _extract_advance_payment_percent(full_text),
        "contract_value_inr": _extract_contract_value_inr(full_text),
        "termination_notice_months": _extract_termination_notice_months(full_text),
    }


# ---------------------------------------------------------------------------
# Rule validators (unchanged from original — fully deterministic Python)
# ---------------------------------------------------------------------------

def _fail(code: str, name: str, severity: str, detail: str, value: Any = None) -> dict:
    entry: dict = {"rule_code": code, "name": name, "result": "fail", "severity": severity, "detail": detail}
    if value is not None:
        entry["value"] = value
    return entry


def _not_found(code: str, name: str, severity: str) -> dict:
    return {"rule_code": code, "name": name, "result": "not_found", "severity": severity}


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

    return []


def _validate_custom(code: str, cfg: dict, name: str, severity: str,
                     extracted: dict, today: date) -> list[dict]:
    rule_type = cfg.get("type", "")

    # Date rules default to agreement_date when no explicit field is configured
    _date_default = "agreement_date"
    field = cfg.get("field") or (_date_default if rule_type in ("date_future", "date_past") else None)

    # boolean_present without a field: treat as a generic "clause present" check
    if rule_type == "boolean_present":
        field_key = cfg.get("field", "")
        val = extracted.get(field_key) if field_key else None
        # If nothing was configured, we cannot extract, so report not_found
        if not field_key:
            return [_not_found(code, name, severity)]
        if val is None:
            return [_fail(code, name, severity, f"Required clause '{name}' was not found in the contract")]
        return []

    if not field:
        return [_not_found(code, name, severity)]

    val = extracted.get(field)
    field_label = next((f["label"] for f in [
        {"value": "agreement_duration_months", "label": "Agreement Duration"},
        {"value": "agreement_date", "label": "Agreement Date"},
        {"value": "dispute_court_city", "label": "Dispute Court City"},
        {"value": "advance_payment_percent", "label": "Advance Payment %"},
        {"value": "contract_value_inr", "label": "Contract Value (INR)"},
        {"value": "termination_notice_months", "label": "Termination Notice"},
    ] if f["value"] == field), field)

    if rule_type == "numeric_range":
        low, high = cfg.get("min"), cfg.get("max")
        if val is None:
            return [_not_found(code, name, severity)]
        if low is not None and val < low:
            return [_fail(code, name, severity, f"{field_label}: {val} is below minimum {low}", val)]
        if high is not None and val > high:
            return [_fail(code, name, severity, f"{field_label}: {val} exceeds maximum {high}", val)]
        return []

    if rule_type == "max_value":
        max_v = cfg.get("max")
        if val is None:
            return [_not_found(code, name, severity)]
        if max_v is not None and val > max_v:
            return [_fail(code, name, severity, f"{field_label}: {val} exceeds maximum {max_v}", val)]
        return []

    if rule_type == "min_value":
        min_v = cfg.get("min")
        if val is None:
            return [_not_found(code, name, severity)]
        if min_v is not None and val < min_v:
            return [_fail(code, name, severity, f"{field_label}: {val} is below minimum {min_v}", val)]
        return []

    if rule_type == "string_allowlist":
        allowed = [v.lower() for v in cfg.get("allowed_values", [])]
        if val is None:
            return [_not_found(code, name, severity)]
        if str(val).lower() not in allowed:
            return [_fail(code, name, severity,
                          f"{field_label}: '{val}' not in allowed list: {cfg.get('allowed_values', [])}", val)]
        return []

    if rule_type == "date_future":
        if val is None:
            return [_not_found(code, name, severity)]
        try:
            val_date = datetime.strptime(str(val), "%Y-%m-%d").date()
            if val_date <= today:
                return [_fail(code, name, severity, f"{field_label}: {val} is not a future date", val)]
        except ValueError:
            return [_not_found(code, name, severity)]
        return []

    if rule_type == "date_past":
        if val is None:
            return [_not_found(code, name, severity)]
        try:
            val_date = datetime.strptime(str(val), "%Y-%m-%d").date()
            if val_date >= today:
                return [_fail(code, name, severity, f"{field_label}: {val} is not in the past", val)]
        except ValueError:
            return [_not_found(code, name, severity)]
        return []

    return [_not_found(code, name, severity)]


_BUILTIN_CODES = {"A", "B", "C", "D", "E", "F"}


def _validate_rules(extracted: dict, rules: list[dict]) -> list[dict]:
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
        full_text = context.get("full_text", "")
        rules = context.get("rules", [])

        self._log_run_start(project_id, tenant_id)

        # Phase 1: Regex-based extraction (no API call)
        extracted = _extract_all_fields(full_text)
        logger.info("checklist_extracted", project_id=project_id, extracted=extracted)

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
            eff_severity = severity if result == "fail" else FindingSeverity.INFO
            findings.append(self._build_finding(
                flag_type="checklist_violation",
                severity=eff_severity,
                title=title,
                description=failure.get("detail", f"Value not found for rule {failure['rule_code']}"),
                recommendation=f"Review the {failure['name']} clause and ensure compliance.",
                confidence=0.90 if result == "fail" else 0.55,
                reasoning_trace=f"Regex-extracted values: {extracted}",
                risk_score={"critical": 9, "high": 7, "medium": 5, "low": 3, "info": 1}.get(eff_severity, 5),
            ))

        self._log_run_complete(project_id, len(findings))

        return {
            "findings": findings,
            "extracted_values": extracted,
            "token_usage": {"input_tokens": 0, "output_tokens": 0},
            "model_version": "python-regex-demo",
            "prompt_version": PROMPT_VERSION,
        }
