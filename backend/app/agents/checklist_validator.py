"""
Agent 4: Checklist Validator (demo mode — no API keys required)

Two-phase validation using pure Python:
1. Regex extraction: extracts dates, durations, amounts, courts, payment days from contract text
2. Python rules engine: deterministically validates each extracted value against
   per-tenant ChecklistRule configs.
"""

import re
from datetime import date, datetime
from typing import Any

from app.agents.base_agent import PROMPT_VERSION, BaseAgent
from app.agents import suggestion_builder as sb
from app.core.constants import FindingSeverity
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Word-to-number mapping for ordinals and cardinals used in contracts
# ---------------------------------------------------------------------------

_WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "twenty-one": 21, "twenty-two": 22, "twenty-three": 23, "twenty-four": 24,
    "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27, "twenty-eight": 28,
    "twenty-nine": 29, "thirty": 30, "thirty-one": 31, "thirty-two": 32,
    "thirty-three": 33, "thirty-four": 34, "thirty-five": 35, "thirty-six": 36,
    "thirty-seven": 37, "thirty-eight": 38, "thirty-nine": 39,
    "forty": 40, "forty-one": 41, "forty-two": 42, "forty-five": 45,
    "forty-eight": 48, "fifty": 50, "fifty-four": 54,
    "sixty": 60, "sixty-six": 66, "seventy": 70, "seventy-two": 72,
    "seventy-five": 75, "eighty": 80, "eighty-four": 84,
    "ninety": 90, "ninety-six": 96, "one hundred": 100, "hundred": 100,
    # Ordinals  (thirty (30) — written form with digit in parentheses)
}

_INDIAN_VALUE_WORDS = {
    "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000,
    "crore": 10_000_000, "crores": 10_000_000,
    "million": 1_000_000, "billion": 1_000_000_000,
}


def _word_to_num(word: str) -> float | None:
    """Convert a written number (possibly with parenthetical digit) to float."""
    w = word.strip().lower()
    # Direct map
    if w in _WORD_TO_NUM:
        return float(_WORD_TO_NUM[w])
    # "twenty (20)" — take the parenthetical digit
    m = re.search(r"\((\d+)\)", word)
    if m:
        return float(m.group(1))
    # Pure digit
    try:
        return float(re.sub(r"[,\s]", "", w))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Date extraction
# ---------------------------------------------------------------------------

_MONTH_MAP = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"], 1
)}


def _extract_dates(text: str) -> list[date]:
    results = []
    seen = set()

    def _add(d: date) -> None:
        k = d.isoformat()
        if k not in seen:
            seen.add(k)
            results.append(d)

    # YYYY-MM-DD
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        try:
            _add(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            pass
    # DD/MM/YYYY
    for m in re.finditer(r"\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b", text):
        try:
            _add(date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
        except ValueError:
            pass
    # 1st January 2025 / 01 June 2026
    for m in re.finditer(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|"
        r"August|September|October|November|December)\s+(\d{4})\b", text, re.IGNORECASE
    ):
        try:
            _add(date(int(m.group(3)), _MONTH_MAP[m.group(2).capitalize()], int(m.group(1))))
        except (ValueError, KeyError):
            pass
    # January 25, 2025
    for m in re.finditer(
        r"\b(January|February|March|April|May|June|July|August|September|October|"
        r"November|December)\s+(\d{1,2}),?\s+(\d{4})\b", text, re.IGNORECASE
    ):
        try:
            _add(date(int(m.group(3)), _MONTH_MAP[m.group(1).capitalize()], int(m.group(2))))
        except (ValueError, KeyError):
            pass
    # "Effective Date: 01 June 2026" — common in contracts
    for m in re.finditer(
        r"effective\s+date[\"'\s:]+(\d{1,2})\s+(January|February|March|April|May|June|July|"
        r"August|September|October|November|December)\s+(\d{4})", text, re.IGNORECASE
    ):
        try:
            _add(date(int(m.group(3)), _MONTH_MAP[m.group(2).capitalize()], int(m.group(1))))
        except (ValueError, KeyError):
            pass
    return results


# ---------------------------------------------------------------------------
# Duration extraction — handles both digit and word forms
# ---------------------------------------------------------------------------

def _extract_duration_months(text: str) -> float | None:
    """Extract contract duration in months. Handles digit AND written-word forms."""
    # Digit form: "24 months", "24-month term"
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*[\-\s]?month", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    # Digit form: "2 years"
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*[\-\s]?year", text, re.IGNORECASE)
    if m:
        return float(m.group(1)) * 12

    # Written-word form: "twenty-four (24) months", "forty-eight months", "thirty-six months"
    word_pattern = (
        r"\b(twenty[- ]four|twenty[- ]five|twenty[- ]six|twenty[- ]seven|twenty[- ]eight|twenty[- ]nine|"
        r"thirty[- ]six|thirty[- ]one|thirty[- ]two|thirty[- ]five|"
        r"forty[- ]eight|forty[- ]five|forty[- ]two|"
        r"sixty|seventy[- ]two|eighty[- ]four|ninety[- ]six|"
        r"twelve|eighteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
        r"one\s+hundred)"
        r"(?:\s*\(\d+\))?\s*[\-\s]?month"
    )
    m = re.search(word_pattern, text, re.IGNORECASE)
    if m:
        v = _word_to_num(m.group(1))
        if v is not None:
            return v
    # "two years" / "three years"
    year_word = r"\b(one|two|three|four|five|six|seven|eight|nine|ten)(?:\s*\(\d+\))?\s*[\-\s]?year"
    m = re.search(year_word, text, re.IGNORECASE)
    if m:
        v = _word_to_num(m.group(1))
        if v is not None:
            return v * 12
    return None


# ---------------------------------------------------------------------------
# Court city extraction
# ---------------------------------------------------------------------------

def _extract_court_city(text: str) -> str | None:
    cities = [
        "mumbai", "delhi", "new delhi", "bangalore", "bengaluru", "hyderabad",
        "chennai", "kolkata", "pune", "ahmedabad", "surat", "jaipur",
        "lucknow", "nagpur", "bhopal", "chandigarh", "kochi",
    ]
    # Look specifically in jurisdiction / governing law / dispute resolution clauses
    dispute_section = ""
    for pat in [
        r"(?:jurisdiction|governing law|dispute resolution|arbitration|courts?)[^\n]{0,400}",
        r"courts?\s+(?:at|of|in)\s+[^\n]{0,100}",
        r"seat\s+(?:of\s+arbitration|and\s+venue)[^\n]{0,100}",
        r"exclusive\s+jurisdiction[^\n]{0,100}",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            dispute_section += " " + m.group(0)

    search_in = dispute_section if dispute_section else text

    # Multi-word cities first
    for city in sorted(cities, key=len, reverse=True):
        if re.search(r"\b" + re.escape(city) + r"\b", search_in, re.IGNORECASE):
            return city.lower()

    # Generic "courts of <City>" pattern
    m = re.search(r"\bcourts?\s+(?:of|at|in)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)", text)
    if m:
        return m.group(1).lower()
    return None


# ---------------------------------------------------------------------------
# Advance payment %
# ---------------------------------------------------------------------------

def _extract_advance_payment_percent(text: str) -> float | None:
    patterns = [
        # "advance payment shall not exceed thirty percent (30%)"
        r"\badvance\b[^.]{0,80}?(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*(?:advance|upfront|mobilization)",
        r"\badvance\b[^.]{0,80}?(ten|twenty|thirty|forty|fifty)\s*(?:percent|\((\d+)\s*%\))",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            # Try digit group first
            for g in range(1, 4):
                try:
                    val = m.group(g)
                    if val and re.match(r"^\d", val):
                        return float(val)
                    elif val:
                        v = _word_to_num(val)
                        if v is not None:
                            return v
                except IndexError:
                    pass
    return None


# ---------------------------------------------------------------------------
# Contract value in INR — handles Indian number words
# ---------------------------------------------------------------------------

def _extract_contract_value_inr(text: str) -> float | None:
    # Digit with Indian suffixes: "₹50,00,000" / "Rs. 75 Lakhs" / "INR 1 Crore"
    currency = r"(?:Rs\.?|INR|₹|Rupees?|Indian\s+Rupees?)"

    # Currency symbol + digit + word suffix
    m = re.search(
        currency + r"\s*([\d,]+(?:\.\d+)?)\s+(crore|lakh|lac|million)",
        text, re.IGNORECASE
    )
    if m:
        num = float(m.group(1).replace(",", ""))
        mult = _INDIAN_VALUE_WORDS.get(m.group(2).lower(), 1)
        return num * mult

    # "Indian Rupees Fifty Lakhs (₹50,00,000)" — word form + parenthetical
    m = re.search(
        r"(?:Indian\s+Rupees?|Rs\.?|INR)\s+"
        r"(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Twenty|Thirty|Forty|Fifty|"
        r"Sixty|Seventy|Eighty|Ninety|One\s+Hundred|One\s+Crore|Seventy[- ]Five)"
        r"\s+(Crore|Lakh|Lac|Million)"
        r"(?:\s*\((?:₹|Rs\.?|INR)?\s*([\d,]+)\))?",
        text, re.IGNORECASE
    )
    if m:
        # Prefer parenthetical digit if present
        if m.group(3):
            return float(m.group(3).replace(",", ""))
        num = _word_to_num(m.group(1))
        if num is None:
            return None
        mult = _INDIAN_VALUE_WORDS.get(m.group(2).lower(), 1)
        return num * mult

    # "₹50,00,000" pure digit (Indian comma grouping)
    m = re.search(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)\b", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", ""))

    return None


# ---------------------------------------------------------------------------
# Payment days — handles digit AND word forms
# ---------------------------------------------------------------------------

def _extract_payment_days(text: str) -> float | None:
    """Extract payment terms in days. Returns number of days."""
    # Look specifically in payment clause context
    payment_context = ""
    for pat in [
        r"(?:payment\s+terms?|shall\s+pay|pay\s+the\s+vendor|invoice)[^\n.]{0,300}",
        r"within\s+(?:\w+\s+){0,5}days?\s+of\s+(?:receipt|invoice)",
    ]:
        for m in re.finditer(pat, text, re.IGNORECASE):
            payment_context += " " + m.group(0)

    search_in = payment_context if payment_context else text

    # Digit form: "within 30 days", "thirty (30) days"
    m = re.search(r"within\s+(\d+)\s*[\-\s]?day", search_in, re.IGNORECASE)
    if m:
        return float(m.group(1))

    # "thirty (30) days" — word with parenthetical
    word_days = (
        r"\b(thirty|forty[- ]five|forty|sixty|ninety|twenty|forty[- ]five|"
        r"fourteen|twenty[- ]one|forty[- ]five|sixty[- ])\s*(?:\(\d+\))?\s*days?"
    )
    m = re.search(word_days, search_in, re.IGNORECASE)
    if m:
        v = _word_to_num(m.group(1))
        if v is not None:
            return v

    # Generic written number + days in payment context
    generic = (
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
        r"fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|twenty[- ]\w+|"
        r"thirty|thirty[- ]\w+|forty|forty[- ]\w+|fifty|sixty|seventy|eighty|ninety)"
        r"(?:\s*\((\d+)\))?\s*[\-\s]?days?"
    )
    for m in re.finditer(generic, search_in, re.IGNORECASE):
        # Prefer parenthetical digit
        if m.group(2):
            return float(m.group(2))
        v = _word_to_num(m.group(1))
        if v is not None:
            return v

    return None


# ---------------------------------------------------------------------------
# Termination notice
# ---------------------------------------------------------------------------

def _extract_termination_notice_months(text: str) -> float | None:
    # Look in termination clause context
    term_context = ""
    for pat in [r"(?:terminat|cancel)[^\n.]{0,300}"]:
        for m in re.finditer(pat, text, re.IGNORECASE):
            term_context += " " + m.group(0)
    search_in = term_context if term_context else text

    # Month patterns (digit)
    m = re.search(
        r"(?:notice|prior written notice|written notice)\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*[\-\s]?month",
        search_in, re.IGNORECASE
    )
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*[\-\s]?month(?:s)?\s+(?:\w+\s+){0,3}notice", search_in, re.IGNORECASE)
    if m:
        return float(m.group(1))

    # Day patterns (digit) → convert to months
    day_patterns = [
        r"(?:notice|prior.*?notice|written notice)\s+(?:of\s+)?(\d+)\s*[\-\s]?day",
        r"(\d+)\s*[\-\s]?day(?:s)?\s+(?:\w+\s+){0,2}(?:prior\s+)?(?:written\s+)?notice",
    ]
    for p in day_patterns:
        m = re.search(p, search_in, re.IGNORECASE)
        if m:
            return round(float(m.group(1)) / 30, 2)

    # Written-word day form: "sixty (60) days' prior written notice"
    word_days = (
        r"\b(seven|fourteen|fifteen|thirty|forty[- ]five|sixty|ninety)"
        r"(?:\s*\((\d+)\))?\s*[\-\s]?days?['\s]+(?:\w+\s+){0,3}notice"
    )
    m = re.search(word_days, search_in, re.IGNORECASE)
    if m:
        if m.group(2):
            return round(float(m.group(2)) / 30, 2)
        v = _word_to_num(m.group(1))
        if v is not None:
            return round(v / 30, 2)

    return None


# ---------------------------------------------------------------------------
# Master extractor
# ---------------------------------------------------------------------------

def _extract_all_fields(full_text: str) -> dict:
    dates = _extract_dates(full_text)
    today = date.today()

    agreement_date = None
    for d in sorted(dates):
        if d <= today:
            agreement_date = d.isoformat()
            break
        # Also accept future dates as the agreement date (contract dated today or future)
    if agreement_date is None and dates:
        agreement_date = sorted(dates)[0].isoformat()

    payment_days = _extract_payment_days(full_text)

    return {
        "agreement_duration_months": _extract_duration_months(full_text),
        "agreement_date": agreement_date,
        "dispute_court_city": _extract_court_city(full_text),
        "advance_payment_percent": _extract_advance_payment_percent(full_text),
        "contract_value_inr": _extract_contract_value_inr(full_text),
        "termination_notice_months": _extract_termination_notice_months(full_text),
        "payment_days": payment_days,
    }


# ---------------------------------------------------------------------------
# Rule validators
# ---------------------------------------------------------------------------

def _fail(code: str, name: str, severity: str, detail: str, value: Any = None,
          target: str | None = None) -> dict:
    entry: dict = {"rule_code": code, "name": name, "result": "fail", "severity": severity, "detail": detail}
    if value is not None:
        entry["value"] = value
    if target is not None:
        entry["target"] = target      # human-readable required value (for suggestions)
    return entry


def _not_found(code: str, name: str, severity: str) -> dict:
    return {"rule_code": code, "name": name, "result": "not_found", "severity": severity}


def _validate_builtin(code: str, cfg: dict, name: str, severity: str,
                      extracted: dict, today: date) -> list[dict]:
    if code == "A":
        val = extracted.get("agreement_duration_months")
        if val is None:
            return [_not_found(code, name, severity)]
        mn, mx = cfg.get("min_months", 12), cfg.get("max_months", 36)
        if not (mn <= val <= mx):
            return [_fail(code, name, severity, f"Duration {val:.0f} months — outside allowed range {mn}–{mx} months", val,
                          target=f"{mn}–{mx} months")]
        return []

    if code == "B":
        val_str = extracted.get("agreement_date")
        if val_str is None:
            return [_not_found(code, name, severity)]
        try:
            val_date = datetime.strptime(val_str, "%Y-%m-%d").date()
            if val_date < today:
                return [_fail(code, name, severity, f"Agreement date {val_str} is in the past", val_str)]
        except ValueError:
            return [_not_found(code, name, severity)]
        return []

    if code == "C":
        val = extracted.get("dispute_court_city")
        allowed = [c.lower() for c in cfg.get("allowed_cities", ["mumbai"])]
        if val is None:
            return [_not_found(code, name, severity)]
        if val.lower() not in allowed:
            allowed_disp = ", ".join(c.title() for c in allowed)
            return [_fail(code, name, severity, f"Court city '{val}' not in allowed cities: {allowed}", val,
                          target=allowed_disp)]
        return []

    if code == "D":
        val = extracted.get("advance_payment_percent")
        max_pct = cfg.get("max_percent", 10)
        if val is None:
            return [_not_found(code, name, severity)]
        if val > max_pct:
            return [_fail(code, name, severity, f"Advance payment {val:.0f}% exceeds maximum {max_pct}%", val,
                          target=f"≤ {max_pct}%")]
        return []

    if code == "E":
        val = extracted.get("contract_value_inr")
        max_val = cfg.get("max_value_inr", 5_000_000)
        if val is None:
            return [_not_found(code, name, severity)]
        if val >= max_val:
            lakh = val / 100_000
            max_lakh = max_val / 100_000
            return [_fail(code, name, severity,
                          f"Contract value ₹{lakh:.0f}L meets or exceeds threshold ₹{max_lakh:.0f}L", val,
                          target=f"below ₹{max_lakh:.0f}L")]
        return []

    if code == "F":
        val = extracted.get("termination_notice_months")
        if val is None:
            return [_not_found(code, name, severity)]
        mn, mx = cfg.get("min_months", 1), cfg.get("max_months", 3)
        if not (mn <= val <= mx):
            days = round(val * 30)
            return [_fail(code, name, severity,
                          f"Termination notice {days} days — outside allowed range {round(mn*30)}–{round(mx*30)} days", val,
                          target=f"{round(mn*30)}–{round(mx*30)} days")]
        return []

    return []


def _validate_custom(code: str, cfg: dict, name: str, severity: str,
                     extracted: dict, today: date) -> list[dict]:
    rule_type = cfg.get("type", "")
    _date_default = "agreement_date"
    field = cfg.get("field") or (_date_default if rule_type in ("date_future", "date_past") else None)

    if rule_type == "boolean_present":
        field_key = cfg.get("field", "")
        val = extracted.get(field_key) if field_key else None
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
        {"value": "payment_days", "label": "Payment Days"},
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


# ---------------------------------------------------------------------------
# Also check payment days against MSME limit directly
# ---------------------------------------------------------------------------

def _check_payment_days(extracted: dict, full_text: str) -> list[dict]:
    """
    Built-in MSME payment check: if payment_days > 45, flag it.
    This runs in addition to checklist rules so it always fires
    even if no custom rule covers it.
    """
    days = extracted.get("payment_days")
    if days is None:
        return []
    failures = []
    if days > 45:
        failures.append({
            "rule_code": "MSME_PAY",
            "name": "Payment Terms (MSME Limit)",
            "result": "fail",
            "severity": "high",
            "detail": f"Payment terms of {int(days)} days exceeds the MSME Act limit of 45 days",
            "value": days,
            "target": "≤ 45 days",
        })
    if days > 30:
        failures.append({
            "rule_code": "PAY_STD",
            "name": "Payment Terms (Standard 30 days)",
            "result": "fail",
            "severity": "medium",
            "detail": f"Payment terms of {int(days)} days exceeds standard 30-day terms",
            "value": days,
            "target": "≤ 30 days",
        })
    return failures


class ChecklistValidatorAgent(BaseAgent):
    name = "checklist_validator"

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        project_id = context["project_id"]
        tenant_id = context["tenant_id"]
        full_text = context.get("full_text", "")
        rules = context.get("rules", [])

        self._log_run_start(project_id, tenant_id)

        extracted = _extract_all_fields(full_text)
        logger.info("checklist_extracted", project_id=project_id, extracted=extracted)

        failures = _validate_rules(extracted, rules)
        # Always check payment days independently
        failures += _check_payment_days(extracted, full_text)

        severity_map = {
            "critical": FindingSeverity.CRITICAL,
            "high": FindingSeverity.HIGH,
            "medium": FindingSeverity.MEDIUM,
            "low": FindingSeverity.LOW,
            "info": FindingSeverity.INFO,
        }

        findings = []
        for failure in failures:
            result = failure["result"]
            sev_str = failure["severity"].lower()
            eff_severity = severity_map.get(sev_str, FindingSeverity.MEDIUM) if result == "fail" else FindingSeverity.INFO
            title = (
                f"Rule {failure['rule_code']} — {failure['name']}: "
                + ("Not extractable" if result == "not_found" else "FAILED")
            )
            value_info = f" Extracted value: {failure.get('value')}" if failure.get("value") is not None and result == "fail" else ""

            # Build a suggestion only for actual failures (not "not_found"),
            # using the exact target the checklist rule requires.
            suggestion = None
            priority = None
            if result == "fail":
                suggestion = sb.for_checklist(
                    rule_name=failure["name"],
                    detail=failure.get("detail", ""),
                    target_hint=failure.get("target"),
                    extracted_value=failure.get("value"),
                    severity=sev_str,
                ).as_dict()
                priority = sb.priority_for(eff_severity)

            findings.append(self._build_finding(
                flag_type="checklist_violation",
                severity=eff_severity,
                title=title,
                description=failure.get("detail", f"Value not found for rule {failure['rule_code']}") + value_info,
                recommendation=f"Review the {failure['name']} clause and ensure it complies with company policy and applicable law.",
                confidence=0.92 if result == "fail" else 0.50,
                reasoning_trace=f"Extracted values: {extracted}",
                risk_score={"critical": 9, "high": 7, "medium": 5, "low": 3, "info": 1}.get(eff_severity, 5),
                suggestion=suggestion,
                priority=priority,
            ))

        self._log_run_complete(project_id, len(findings))

        return {
            "findings": findings,
            "extracted_values": extracted,
            "token_usage": {"input_tokens": 0, "output_tokens": 0},
            "model_version": "python-regex-v2-demo",
            "prompt_version": PROMPT_VERSION,
        }
