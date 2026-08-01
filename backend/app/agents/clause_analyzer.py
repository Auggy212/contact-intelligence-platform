"""
Clause Analyzer — deterministic, offline, no API keys required.

Provides four capabilities used by all comparison agents:
  1. ClauseClassifier   — assigns a ClauseType to every parsed clause
  2. ValueExtractor     — extracts structured values (numbers, %, INR, dates,
                          durations, party names) from any clause text,
                          with type-specific extraction hints per ClauseType
  3. ValueDiffEngine    — compares extracted values between two matched clauses
                          and emits structured ValueChange records; fires even
                          when overall text similarity is high
  4. ConfidenceScorer   — evidence-based confidence, never hardcoded

Design constraint: pure Python + regex. No embeddings, no LLMs, no external calls.
Designed so that replacing ValueExtractor internals with Voyage embeddings later
requires only swapping the extraction step, not the diff or classification logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.core.constants import FindingSeverity


# ─────────────────────────────────────────────────────────────────────────────
# 1. CLAUSE TYPE
# ─────────────────────────────────────────────────────────────────────────────

class ClauseType(StrEnum):
    PAYMENT           = "payment"
    TERMINATION       = "termination"
    LIABILITY         = "liability"
    INDEMNITY         = "indemnity"
    CONFIDENTIALITY   = "confidentiality"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    WARRANTY          = "warranty"
    JURISDICTION      = "jurisdiction"
    DATA_PROTECTION   = "data_protection"
    INSURANCE         = "insurance"
    FORCE_MAJEURE     = "force_majeure"
    ASSIGNMENT        = "assignment"
    AUDIT_RIGHTS      = "audit_rights"
    EXCLUSIVITY       = "exclusivity"
    NON_COMPETE       = "non_compete"
    NON_SOLICITATION  = "non_solicitation"
    DATA_RETENTION    = "data_retention"
    GOVERNING_LAW     = "governing_law"
    CHANGE_OF_CONTROL = "change_of_control"
    RENEWAL           = "renewal"
    SERVICE_CREDITS   = "service_credits"
    ESCALATION        = "escalation"
    SUBCONTRACTING    = "subcontracting"
    SLA               = "sla"
    DEFINITIONS       = "definitions"
    SCOPE             = "scope"
    REPRESENTATIONS   = "representations"
    DISPUTE_RESOLUTION = "dispute_resolution"
    GENERAL           = "general"
    MISCELLANEOUS     = "miscellaneous"


# ─── Heading keyword rules (checked first — fastest) ─────────────────────────
_HEADING_RULES: list[tuple[re.Pattern, ClauseType]] = [
    (re.compile(r"\bpayment\b|\binvoice\b|\bfees?\b|\bprice\b|\bcompensation\b", re.I), ClauseType.PAYMENT),
    (re.compile(r"\btermination\b|\bterminate\b|\bnotice\s+period\b", re.I), ClauseType.TERMINATION),
    (re.compile(r"\bliabilit\w+\b|\blimit\w*\s+of\s+liabilit\w+\b|\bindemnif\w+\b", re.I), ClauseType.LIABILITY),
    (re.compile(r"\bindemnif\w+\b|\bhold\s+harmless\b", re.I), ClauseType.INDEMNITY),
    (re.compile(r"\bconfidential\w*\b|\bnon[- ]?disclosure\b|\bnda\b", re.I), ClauseType.CONFIDENTIALITY),
    (re.compile(r"\bintellectual\s+property\b|\bip\s+rights?\b|\bcopyright\b|\bpatent\b|\btrademark\b", re.I), ClauseType.INTELLECTUAL_PROPERTY),
    (re.compile(r"\bwarrant\w+\b|\brepresent\w*\s+and\s+warrant\w*\b", re.I), ClauseType.WARRANTY),
    (re.compile(r"\bjurisdiction\b|\bgoverning\s+court\b|\bseat\s+of\b", re.I), ClauseType.JURISDICTION),
    (re.compile(r"\bdata\s+protection\b|\bpersonal\s+data\b|\bprivacy\b|\bgdpr\b|\bdpdp\b", re.I), ClauseType.DATA_PROTECTION),
    (re.compile(r"\binsurance\b|\bpolicy\b.{0,20}\bcover\w*\b", re.I), ClauseType.INSURANCE),
    (re.compile(r"\bforce\s+majeure\b|\bact\s+of\s+god\b|\bcircumstances\s+beyond\b", re.I), ClauseType.FORCE_MAJEURE),
    (re.compile(r"\bassignment\b|\bassign\b|\btransfer\b.{0,30}\bright\b", re.I), ClauseType.ASSIGNMENT),
    (re.compile(r"\baudit\b|\binspection\s+rights?\b|\bbooks\s+and\s+records\b", re.I), ClauseType.AUDIT_RIGHTS),
    (re.compile(r"\bexclusiv\w+\b", re.I), ClauseType.EXCLUSIVITY),
    (re.compile(r"\bnon[- ]?compet\w+\b|\bnot\s+to\s+compet\w+\b", re.I), ClauseType.NON_COMPETE),
    (re.compile(r"\bnon[- ]?solicit\w+\b|\bnot\s+to\s+solicit\b", re.I), ClauseType.NON_SOLICITATION),
    (re.compile(r"\bdata\s+retention\b|\bretention\s+period\b|\bdelete\s+data\b", re.I), ClauseType.DATA_RETENTION),
    (re.compile(r"\bgoverning\s+law\b|\bapplicable\s+law\b|\bchoice\s+of\s+law\b", re.I), ClauseType.GOVERNING_LAW),
    (re.compile(r"\bchange\s+of\s+control\b|\bchange\s+in\s+control\b|\bacquisition\b", re.I), ClauseType.CHANGE_OF_CONTROL),
    (re.compile(r"\brenewal\b|\bauto[- ]?renew\b|\bextension\b.{0,20}\bterm\b", re.I), ClauseType.RENEWAL),
    (re.compile(r"\bservice\s+credit\w*\b|\bsla\s+credit\b|\brebate\b", re.I), ClauseType.SERVICE_CREDITS),
    (re.compile(r"\bescalation\b|\bescalat\w+\s+process\b", re.I), ClauseType.ESCALATION),
    (re.compile(r"\bsubcontract\w*\b|\bsubvendor\b|\bthird[- ]party\s+provider\b", re.I), ClauseType.SUBCONTRACTING),
    (re.compile(r"\bservice\s+level\b|\bsla\b|\buptime\b|\bavailabilit\w+\b|\bresponse\s+time\b", re.I), ClauseType.SLA),
    (re.compile(r"\bdefinition\b|\bmeans\b.*\bshall\b|\binterpretation\b", re.I), ClauseType.DEFINITIONS),
    (re.compile(r"\bscope\b|\bservices?\s+description\b|\bstatement\s+of\s+work\b|\bsow\b", re.I), ClauseType.SCOPE),
    (re.compile(r"\brepresent\w*\s+and\s+warrant\w*\b|\brepresentations?\b", re.I), ClauseType.REPRESENTATIONS),
    (re.compile(r"\bdispute\b|\barbitrat\w+\b|\bmediat\w+\b|\bconciliat\w+\b", re.I), ClauseType.DISPUTE_RESOLUTION),
    (re.compile(r"\bgeneral\s+provision\b|\bmiscellaneous\b|\bboilerplate\b", re.I), ClauseType.GENERAL),
]

# ─── Body keyword rules (fallback when heading is absent/ambiguous) ───────────
_BODY_RULES: list[tuple[re.Pattern, ClauseType]] = [
    (re.compile(r"\bshall\s+pay\b.{0,60}\bdays?\b|\binvoice\b.{0,60}\bdays?\b", re.I), ClauseType.PAYMENT),
    (re.compile(r"\bterminate\b.{0,80}\bnotice\b|\bnotice\b.{0,40}\bterminate\b", re.I), ClauseType.TERMINATION),
    (re.compile(r"\baggregate\s+liabilit\w+\b|\bnot\s+exceed.{0,30}\bfees?\b|\bunlimited\s+liabilit\w+\b", re.I), ClauseType.LIABILITY),
    (re.compile(r"\bshall\s+indemnif\w+\b|\bhold\s+harmless\b|\bdefend\b.{0,30}\bindemnif\w+\b", re.I), ClauseType.INDEMNITY),
    (re.compile(r"\bconfidential\s+information\b.{0,60}\bdisclose\b", re.I), ClauseType.CONFIDENTIALITY),
    (re.compile(r"\bintellectual\s+property.{0,50}\bvest\b|\bip\s+rights?\b.{0,50}\bvest\b|\bip\b.{0,30}\bown\w+\b|\ball\s+ip\b", re.I), ClauseType.INTELLECTUAL_PROPERTY),
    (re.compile(r"\bwarrants?\s+that\b|\brepresents?\s+and\s+warrants?\b", re.I), ClauseType.WARRANTY),
    (re.compile(r"\bcourts?\s+(?:at|of|in)\b|\bexclusive\s+jurisdiction\b|\bseat\s+of\s+arbitration\b", re.I), ClauseType.JURISDICTION),
    (re.compile(r"\bpersonal\s+data\b|\bdata\s+subject\b|\bprocessing\b.{0,30}\bpersonal\b", re.I), ClauseType.DATA_PROTECTION),
    (re.compile(r"\binsurance\s+polic\w+\b|\bpremium\b.{0,30}\binsure\w*\b", re.I), ClauseType.INSURANCE),
    (re.compile(r"\bforce\s+majeure\b|\bact\s+of\s+god\b|\bnatural\s+disaster\b", re.I), ClauseType.FORCE_MAJEURE),
    (re.compile(r"\bmay\s+not\s+assign\b|\bcannot\s+assign\b|\bnot\s+assign\b|\btransfer.{0,30}\bagreement\b"
                r"|\bassign.{0,80}without.{0,40}consent\b|\bprior\s+written\s+consent.{0,60}\bassign\b", re.I), ClauseType.ASSIGNMENT),
    (re.compile(r"\bright\s+to\s+audit\b|\bmay\s+inspect\b|\baccess\s+to\s+books\b", re.I), ClauseType.AUDIT_RIGHTS),
    (re.compile(r"\bsolely\b.{0,20}\bexclusive\b|\bexclusive\s+right\b", re.I), ClauseType.EXCLUSIVITY),
    (re.compile(r"\bnot\s+carry\s+on\b|\brefrain\s+from\s+competing\b", re.I), ClauseType.NON_COMPETE),
    (re.compile(r"\bsolicit\b.{0,30}\bemployee\b|\bhire\b.{0,30}\bpersonnel\b", re.I), ClauseType.NON_SOLICITATION),
    (re.compile(r"\bretain\b.{0,30}\bdata\b.{0,30}\bperiod\b|\bdelete\b.{0,30}\bpersonal\s+data\b", re.I), ClauseType.DATA_RETENTION),
    (re.compile(r"\bgoverned\s+by\b.{0,30}\blaws?\s+of\b|\blaws?\s+of\s+india\b", re.I), ClauseType.GOVERNING_LAW),
    (re.compile(r"\bautomatic\w*\s+renew\w*\b|\bauto[- ]?renew\b", re.I), ClauseType.RENEWAL),
    (re.compile(r"\bservice\s+level\s+agreement\b|\bsla\b.{0,20}\buptime\b", re.I), ClauseType.SLA),
    (re.compile(r"\bsubcontract\w*\b|\bthird[- ]party\s+service\b", re.I), ClauseType.SUBCONTRACTING),
    (re.compile(r"\bdispute\b.{0,60}\bnegotiat\w+\b|\barbitrat\w+\s+under\b", re.I), ClauseType.DISPUTE_RESOLUTION),
]


class ClauseClassifier:
    """
    Assigns a ClauseType to a parsed clause using heading + body keyword rules.
    Fast, deterministic, no external calls.

    Upgrade path: replace body_rules matching with voyage-law-2 embedding
    similarity without changing the interface.
    """

    @staticmethod
    def classify(clause: dict) -> ClauseType:
        heading = (clause.get("heading") or "").strip()
        body    = (clause.get("body_text") or "").strip()

        # 1. Heading match (most reliable)
        for pattern, ctype in _HEADING_RULES:
            if pattern.search(heading):
                return ctype

        # 2. Body text match
        for pattern, ctype in _BODY_RULES:
            if pattern.search(body):
                return ctype

        return ClauseType.MISCELLANEOUS

    @staticmethod
    def classify_all(clauses: list[dict]) -> list[dict]:
        """Return clauses with an added 'clause_type' key."""
        result = []
        for c in clauses:
            enriched = dict(c)
            enriched["clause_type"] = ClauseClassifier.classify(c).value
            result.append(enriched)
        return result


# ─────────────────────────────────────────────────────────────────────────────
# 2. VALUE EXTRACTOR
# ─────────────────────────────────────────────────────────────────────────────

_WORD_NUM: dict[str, float] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "twenty-one": 21, "twenty-two": 22, "twenty-three": 23,
    "twenty-four": 24, "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27,
    "twenty-eight": 28, "twenty-nine": 29,
    "thirty": 30, "thirty-one": 31, "thirty-two": 32, "thirty-five": 35,
    "thirty-six": 36, "thirty-eight": 38,
    "forty": 40, "forty-five": 45, "forty-eight": 48, "fifty": 50,
    "fifty-four": 54, "sixty": 60, "seventy": 70, "seventy-two": 72,
    "seventy-five": 75, "eighty": 80, "eighty-four": 84,
    "ninety": 90, "ninety-six": 96, "one hundred": 100, "hundred": 100,
}

_INDIAN_MULT: dict[str, float] = {
    "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5,
    "crore": 1e7, "crores": 1e7,
    "million": 1e6, "billion": 1e9,
}

_MONTH_NAMES = (
    "January|February|March|April|May|June|"
    "July|August|September|October|November|December"
)

_WORD_NUM_RE = re.compile(
    r"\b(one\s+hundred|twenty[- ]\w+|thirty[- ]\w+|forty[- ]\w+|"
    r"fifty[- ]\w+|sixty|seventy[- ]\w+|eighty[- ]\w+|ninety[- ]\w+|"
    r"twenty|thirty|forty|fifty|seventy|eighty|ninety|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"one|two|three|four|five|six|seven|eight|nine|ten)\b",
    re.I,
)


def _resolve_word_num(word: str) -> float | None:
    w = word.strip().lower().replace(" ", "-")
    if w in _WORD_NUM:
        return _WORD_NUM[w]
    w2 = re.sub(r"\s+", "-", word.strip().lower())
    return _WORD_NUM.get(w2)


@dataclass
class ExtractedValues:
    """All structured values found in a clause's body text."""
    # Time durations
    duration_months: float | None = None
    notice_days: float | None = None
    confidentiality_years: float | None = None
    warranty_days: float | None = None
    data_retention_days: float | None = None
    non_compete_months: float | None = None
    non_solicitation_months: float | None = None
    renewal_notice_days: float | None = None
    audit_frequency_months: float | None = None

    # Payment
    payment_days: float | None = None
    advance_percent: float | None = None
    penalty_percent: float | None = None
    interest_rate: float | None = None
    late_payment_interest: float | None = None

    # Monetary
    contract_value_inr: float | None = None
    liability_cap_inr: float | None = None
    insurance_amount_inr: float | None = None
    service_credit_percent: float | None = None

    # Coverage ratios
    liability_cap_months: float | None = None
    sla_uptime_percent: float | None = None
    sla_response_time_hours: float | None = None
    test_coverage_percent: float | None = None

    # Jurisdiction
    court_city: str | None = None
    governing_law: str | None = None
    arbitration_seat: str | None = None

    # Parties / direction
    ip_owner: str | None = None
    indemnity_direction: str | None = None
    assignment_consent: str | None = None   # "required" | "not_required"
    subcontracting_consent: str | None = None  # "required" | "not_required"

    # Dates
    effective_date: str | None = None

    # All raw numbers found (catch-all)
    raw_numbers: list[float] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != []}


class ValueExtractor:
    """
    Extracts structured numeric, monetary, temporal, and categorical values
    from a clause's body_text string, with type-specific extraction hints.

    Priority 2 & 3 implementation: the clause_type parameter activates
    specialised extraction patterns for each category.

    Upgrade path: the interface (extract(text, clause_type)) stays stable.
    Internal implementation can later call an LLM for complex clauses.
    """

    # ── Core extraction helpers ──────────────────────────────────────────────

    @staticmethod
    def _digit_or_word(text: str, context_pat: str, unit_pat: str = "") -> float | None:
        """
        Find a number (digit or written word) preceded by context_pat
        and followed by unit_pat.
        """
        full = context_pat + r"\s*(\d+(?:\.\d+)?)\s*" + unit_pat
        m = re.search(full, text, re.I | re.DOTALL)
        if m:
            return float(m.group(1))
        word_par = (context_pat + r"\s*(" + _WORD_NUM_RE.pattern[2:-2] +
                    r")\s*\((\d+)\)\s*" + unit_pat)
        m = re.search(word_par, text, re.I | re.DOTALL)
        if m:
            return float(m.group(len(m.groups())))
        word_only = context_pat + r"\s*(" + _WORD_NUM_RE.pattern[2:-2] + r")\s*" + unit_pat
        m = re.search(word_only, text, re.I | re.DOTALL)
        if m:
            return _resolve_word_num(m.group(1))
        return None

    @staticmethod
    def _inr_amount(text: str, context_hint: str = "") -> float | None:
        """Extract the first INR monetary amount, with optional context.

        If a context_hint is given but is NOT present in the text, return None
        immediately. Falling back to a whole-clause scan is the root cause of
        cross-field contamination (e.g. a liability clause grabbing a contract
        value stated elsewhere). Only scan the whole clause when no hint is set.
        """
        search = text
        if context_hint:
            m = re.search(context_hint + r".{0,200}", text, re.I | re.DOTALL)
            if not m:
                return None      # hint not found → this field is not in this clause
            search = m.group(0)

        cur = r"(?:Rs\.?|INR|₹|Rupees?|Indian\s+Rupees?)"

        # Priority 1: parenthetical digit form — most reliable
        # "Indian Rupees One Crore Fifty Lakhs (₹1,50,00,000)"
        par_m = re.search(
            r"(?:Indian\s+Rupees?|Rs\.?|INR)\s+[\w\s-]+?\s*"
            r"\((?:₹|Rs\.?|INR)?\s*([\d,]+)\)",
            search, re.I
        )
        if par_m:
            return float(par_m.group(1).replace(",", ""))

        # Priority 2: digit + multiplier suffix
        m = re.search(cur + r"\s*([\d,]+(?:\.\d+)?)\s*(crore|lakh|lac|million|billion)", search, re.I)
        if m:
            return float(m.group(1).replace(",", "")) * _INDIAN_MULT[m.group(2).lower()]

        # Priority 3: compound word form "One Crore Fifty Lakhs" → sum
        # Finds currency prefix then accumulates crore + lakh components
        compound_m = re.search(
            r"(?:Indian\s+Rupees?|Rs\.?|INR)\s+([\w\s-]+)",
            search, re.I
        )
        if compound_m:
            phrase = compound_m.group(1)
            total = 0.0
            # Try crore component
            cr_m = re.search(r"([\w-]+)\s+crore", phrase, re.I)
            if cr_m:
                n = _resolve_word_num(cr_m.group(1))
                if n:
                    total += n * 1e7
            # Try lakh component
            lk_m = re.search(r"([\w-]+)\s+(?:lakh|lac)", phrase, re.I)
            if lk_m:
                n = _resolve_word_num(lk_m.group(1))
                if n:
                    total += n * 1e5
            if total > 0:
                return total

        # Priority 4: plain digit with currency symbol
        m = re.search(cur + r"\s*([\d,]+(?:\.\d+)?)", search, re.I)
        if m:
            return float(m.group(1).replace(",", ""))

        return None

    @staticmethod
    def _percent(text: str, context_hint: str = "") -> float | None:
        search = text
        if context_hint:
            m = re.search(context_hint + r".{0,150}", text, re.I | re.DOTALL)
            if not m:
                return None      # context hint absent → field not in this clause
            search = m.group(0)
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", search, re.I)
        if m:
            return float(m.group(1))
        m = re.search(
            r"(" + "|".join(_WORD_NUM.keys()) + r")\s+percent",
            search, re.I
        )
        if m:
            return _resolve_word_num(m.group(1))
        return None

    @staticmethod
    def _days(text: str, context_hint: str = "") -> float | None:
        search = text
        if context_hint:
            m = re.search(context_hint + r".{0,200}", text, re.I | re.DOTALL)
            if not m:
                return None      # context hint absent → field not in this clause
            search = m.group(0)
        m = re.search(r"\b(\d+)\s*[\-\s]?days?", search, re.I)
        if m:
            return float(m.group(1))
        m = re.search(
            r"(" + "|".join(_WORD_NUM.keys()) + r")\s*(?:\((\d+)\))?\s*[\-\s]?days?",
            search, re.I
        )
        if m:
            if m.group(2):
                return float(m.group(2))
            return _resolve_word_num(m.group(1))
        return None

    @staticmethod
    def _months(text: str, context_hint: str = "") -> float | None:
        search = text
        if context_hint:
            m = re.search(context_hint + r".{0,200}", text, re.I | re.DOTALL)
            if not m:
                return None      # context hint absent → field not in this clause
            search = m.group(0)
        m = re.search(r"\b(\d+)\s*[\-\s]?months?", search, re.I)
        if m:
            return float(m.group(1))
        m = re.search(
            r"(" + "|".join(_WORD_NUM.keys()) + r")\s*(?:\((\d+)\))?\s*[\-\s]?months?",
            search, re.I
        )
        if m:
            if m.group(2):
                return float(m.group(2))
            return _resolve_word_num(m.group(1))
        # years → months
        m = re.search(r"\b(\d+)\s*[\-\s]?years?", search, re.I)
        if m:
            return float(m.group(1)) * 12
        m = re.search(
            r"(" + "|".join(_WORD_NUM.keys()) + r")\s*(?:\((\d+)\))?\s*[\-\s]?years?",
            search, re.I
        )
        if m:
            if m.group(2):
                return float(m.group(2)) * 12
            v = _resolve_word_num(m.group(1))
            return v * 12 if v else None
        return None

    @staticmethod
    def _hours(text: str, context_hint: str = "") -> float | None:
        search = text
        if context_hint:
            m = re.search(context_hint + r".{0,150}", text, re.I | re.DOTALL)
            if not m:
                return None      # context hint absent → field not in this clause
            search = m.group(0)
        m = re.search(r"\b(\d+(?:\.\d+)?)\s*[\-\s]?hours?", search, re.I)
        if m:
            return float(m.group(1))
        m = re.search(
            r"(" + "|".join(_WORD_NUM.keys()) + r")\s*(?:\((\d+)\))?\s*[\-\s]?hours?",
            search, re.I
        )
        if m:
            if m.group(2):
                return float(m.group(2))
            return _resolve_word_num(m.group(1))
        return None

    # ── Public interface ─────────────────────────────────────────────────────

    def extract(self, text: str, clause_type: ClauseType | None = None) -> ExtractedValues:
        """
        Extract all structured values from clause text.

        Priority 3: clause_type activates type-specific extraction branches so
        that, e.g., payment clauses get richer payment analysis and SLA clauses
        get uptime/response-time extraction.
        """
        ev = ExtractedValues()
        t = text
        ctype = clause_type or ClauseType.MISCELLANEOUS

        # ── Always-on extractions (run for every clause type) ─────────────

        # Duration / term. Scoped by leading context hints so it does not grab
        # unrelated durations (notice periods, warranty windows) in the clause.
        ev.duration_months = self._months(
            t, r"(?:remain\s+in\s+force|term\s+of|period\s+of|commence|for\s+a\s+term)"
        )

        # Contract value
        ev.contract_value_inr = self._inr_amount(
            t, r"(?:total\s+contract\s+value|shall\s+not\s+exceed|contract\s+value)"
        )

        # Effective date
        date_m = re.search(
            r"(?:effective\s+date|dated?)\s*[:\"]?\s*"
            r"(\d{1,2})\s+(" + _MONTH_NAMES + r")\s+(\d{4})",
            t, re.I
        )
        if date_m:
            months_map = {mn: i for i, mn in enumerate(
                ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"], 1
            )}
            try:
                ev.effective_date = (
                    f"{date_m.group(3)}-"
                    f"{months_map.get(date_m.group(2).capitalize(), 1):02d}-"
                    f"{int(date_m.group(1)):02d}"
                )
            except Exception:
                pass

        # Raw numbers catch-all
        ev.raw_numbers = [float(n) for n in re.findall(r"\b\d+(?:\.\d+)?\b", t)]

        # ── TYPE-SPECIFIC EXTRACTION BRANCHES ────────────────────────────────
        # Priority 3: specialised checks per ClauseType.
        # IMPORTANT: Fields that are highly prone to false positives (warranty_days,
        # data_retention_days, sla_uptime_percent, etc.) are NOT run for MISCELLANEOUS
        # clauses — only when the clause is correctly typed. High-signal fields
        # (payment_days, notice_days, liability_cap) still run for MISCELLANEOUS
        # because their context patterns are specific enough to avoid cross-matches.

        # ── PAYMENT (also runs for MISCELLANEOUS — context hints are specific) ─
        if ctype in (ClauseType.PAYMENT, ClauseType.MISCELLANEOUS):
            ev.payment_days = self._days(t, r"(?:shall\s+pay|pay\s+the\s+vendor|within|invoice|invoices?)")
            ev.advance_percent = self._percent(t, r"\badvance\b")
            ev.penalty_percent = self._percent(t, r"\bpenalt\w*\s+of\b")
            ev.interest_rate = self._percent(t, r"\binterest\b.{0,30}\brate\b")
            ev.late_payment_interest = self._percent(t, r"\blate\s+payment\b.{0,40}\binterest\b")

        # ── TERMINATION (also runs for MISCELLANEOUS) ─────────────────────────
        if ctype in (ClauseType.TERMINATION, ClauseType.MISCELLANEOUS):
            notice = self._days(t, r"(?:terminat\w*|cancel\w*).{0,100}")
            if notice is None:
                notice = self._days(t, r"(?:prior\s+written\s+notice|written\s+notice)")
            ev.notice_days = notice

        # ── LIABILITY (also runs for MISCELLANEOUS — context hint is specific) ─
        if ctype in (ClauseType.LIABILITY, ClauseType.INDEMNITY, ClauseType.MISCELLANEOUS):
            ev.liability_cap_inr = self._inr_amount(
                t, r"(?:aggregate\s+liabilit\w+|liabilit\w+\s+shall\s+not\s+exceed)"
            )
            ev.liability_cap_months = self._months(
                t, r"(?:aggregate\s+liabilit\w+|liabilit\w+.{0,30}exceed)"
            )

        # ── CONFIDENTIALITY (also runs for MISCELLANEOUS) ─────────────────────
        if ctype in (ClauseType.CONFIDENTIALITY, ClauseType.MISCELLANEOUS):
            conf_months = self._months(t, r"confidential\w*.{0,60}")
            ev.confidentiality_years = round(conf_months / 12, 2) if conf_months else None

        # ── WARRANTY (type-specific only — avoids grabbing term/notice durations) ─
        if ctype == ClauseType.WARRANTY:
            ev.warranty_days = self._days(
                t, r"(?:warrant\w*|defect.{0,20}free|warranty\s+period|defect\s+liability)"
            )
            if ev.warranty_days is None:
                w_months = self._months(t, r"(?:warrant\w*|warranty\s+period)")
                if w_months:
                    ev.warranty_days = w_months * 30

        # ── SLA (type-specific only — "availability" fires too broadly otherwise) ─
        if ctype == ClauseType.SLA:
            ev.sla_uptime_percent = self._percent(t, r"(?:uptime|availability)")
            ev.sla_response_time_hours = self._hours(
                t, r"(?:response\s+time|initial\s+response|first\s+response|acknowledge)"
            )
            if ev.sla_response_time_hours is None:
                m = re.search(r"\b(\d+)\s*minutes?\b", t, re.I)
                if m:
                    ev.sla_response_time_hours = float(m.group(1)) / 60

        # ── INSURANCE (type-specific only) ────────────────────────────────────
        if ctype == ClauseType.INSURANCE:
            ev.insurance_amount_inr = self._inr_amount(t, r"insurance")

        # ── INTELLECTUAL PROPERTY (also runs for MISCELLANEOUS — patterns specific) ─
        if ctype in (ClauseType.INTELLECTUAL_PROPERTY, ClauseType.MISCELLANEOUS):
            if re.search(r"\bvest\b.{0,40}\bclient\b|\bclient.{0,40}\bown\w+\s+all\b", t, re.I):
                ev.ip_owner = "client"
            elif re.search(
                r"\bremain.{0,60}\bvendor\b|\bvendor.{0,60}\bretain\b"
                r"|\bproperty\s+of\s+the\s+vendor\b|\bvendor[‘’]?s?\s+(?:exclusive\s+)?property\b",
                t, re.I
            ):
                ev.ip_owner = "vendor"
            elif re.search(r"\bjoint\b.{0,20}\bown\w+\b|\bshared\s+ip\b", t, re.I):
                ev.ip_owner = "joint"

        # ── INDEMNITY (also runs for MISCELLANEOUS — patterns are specific) ────
        if ctype in (ClauseType.INDEMNITY, ClauseType.MISCELLANEOUS):
            if re.search(r"\bvendor\s+shall\s+indemnif\w+\b", t, re.I):
                ev.indemnity_direction = "vendor_to_client"
            elif re.search(r"\bclient\s+shall\s+(?:fully\s+)?indemnif\w+\b", t, re.I):
                ev.indemnity_direction = "client_to_vendor"

        # ── JURISDICTION / GOVERNING LAW (also runs for MISCELLANEOUS) ────────
        if ctype in (ClauseType.JURISDICTION, ClauseType.GOVERNING_LAW,
                     ClauseType.DISPUTE_RESOLUTION, ClauseType.MISCELLANEOUS):
            # Use known-city matching for court city — avoids greedy open captures
            _KNOWN_CITIES = [
                "new delhi", "mumbai", "bengaluru", "bangalore",
                "hyderabad", "chennai", "kolkata", "pune", "ahmedabad",
                "singapore", "london", "new york",
            ]
            # First try "courts at/of/in <city>" pattern with known cities
            _court_ctx = re.search(
                r"courts?\s+(?:at|of|in)\s+(.{2,30}?)(?:\s+shall|\s+will|\.|,|$)",
                t, re.I
            )
            if _court_ctx:
                candidate = _court_ctx.group(1).strip().lower()
                for city in _KNOWN_CITIES:
                    if city in candidate:
                        ev.court_city = city
                        break
            if ev.court_city is None:
                for city in _KNOWN_CITIES:
                    if re.search(r"\b" + re.escape(city) + r"\b", t, re.I):
                        ev.court_city = city
                        break

            law_m = re.search(r"laws?\s+of\s+([A-Za-z][a-zA-Z\s]{1,28}?)(?:\s+and\s+wales|\.|,|\band\b|\s{2}|$)", t, re.I)
            if law_m:
                ev.governing_law = law_m.group(1).strip().lower()

            # Arbitration seat: look for known cities after seat-of-arbitration phrasing
            _arb_ctx = re.search(
                r"seat\s+of\s+arbitration\s+shall\s+be\s+(.{2,30}?)(?:\.|,|\s+and\b|$)",
                t, re.I
            )
            if _arb_ctx:
                candidate = _arb_ctx.group(1).strip().lower()
                for city in _KNOWN_CITIES:
                    if city in candidate:
                        ev.arbitration_seat = city
                        break
            if ev.arbitration_seat is None:
                arb_ctx2 = re.search(
                    r"(?:arbitration\s+(?:shall\s+be\s+)?(?:held|conducted)\s+(?:at|in))\s+(.{2,30}?)(?:\.|,|$)",
                    t, re.I
                )
                if arb_ctx2:
                    candidate = arb_ctx2.group(1).strip().lower()
                    for city in _KNOWN_CITIES:
                        if city in candidate:
                            ev.arbitration_seat = city
                            break

        # ── NON-COMPETE (type-specific only) ──────────────────────────────────
        if ctype == ClauseType.NON_COMPETE:
            ev.non_compete_months = self._months(
                t, r"(?:non[- ]?compet\w*|compet\w*\s+restrict\w*|restraint).{0,80}"
            )

        # ── NON-SOLICITATION (type-specific only) ─────────────────────────────
        if ctype == ClauseType.NON_SOLICITATION:
            ev.non_solicitation_months = self._months(
                t, r"(?:non[- ]?solicit\w*|solicit.{0,30}restrict\w*).{0,80}"
            )

        # ── DATA RETENTION (type-specific only) ───────────────────────────────
        if ctype in (ClauseType.DATA_RETENTION, ClauseType.DATA_PROTECTION):
            ev.data_retention_days = self._days(
                t, r"(?:retain.{0,20}data|data.{0,20}retain|delete.{0,20}data)"
            )
            if ev.data_retention_days is None:
                ret_months = self._months(
                    t, r"(?:retain.{0,20}data|data.{0,20}retain|retention\s+period)"
                )
                if ret_months:
                    ev.data_retention_days = ret_months * 30

        # ── ASSIGNMENT (type-specific only) ───────────────────────────────────
        if ctype == ClauseType.ASSIGNMENT:
            if re.search(
                r"\bmay\s+not\s+assign\b|\bcannot\s+assign\b|\bnot\s+assign\b|\bno\s+assignment\b"
                r"|\bprior\s+written\s+consent.{0,50}\bassign\b"
                r"|\bassign.{0,50}without.{0,50}(?:prior\s+written\s+)?consent\b",
                t, re.I
            ):
                ev.assignment_consent = "required"
            elif re.search(r"\bmay\s+freely\s+assign\b|\bfreely\s+assign\b"
                           r"|\bassignment.{0,30}\bno\s+consent\b", t, re.I):
                ev.assignment_consent = "not_required"

        # ── SUBCONTRACTING (type-specific only) ───────────────────────────────
        if ctype == ClauseType.SUBCONTRACTING:
            if re.search(r"\bmay\s+not\s+subcontract\b|\bnot\s+permitted\s+to\s+subcontract\b"
                         r"|\bprior\s+written\s+approval.{0,30}\bsubcontract\b", t, re.I):
                ev.subcontracting_consent = "required"
            elif re.search(r"\bmay\s+subcontract\b|\bfreely\s+subcontract\b", t, re.I):
                ev.subcontracting_consent = "not_required"

        # ── RENEWAL (type-specific only) ──────────────────────────────────────
        if ctype == ClauseType.RENEWAL:
            ev.renewal_notice_days = self._days(
                t, r"(?:renewal\s+notice|opt[- ]out|written\s+notice.{0,30}renew\w*"
                   r"|non[- ]?renewal).{0,100}"
            )

        # ── SERVICE CREDITS (type-specific only) ──────────────────────────────
        if ctype in (ClauseType.SERVICE_CREDITS, ClauseType.SLA):
            ev.service_credit_percent = self._percent(
                t, r"(?:service\s+credit|sla\s+credit|rebate).{0,80}"
            )

        # ── AUDIT RIGHTS (type-specific only) ─────────────────────────────────
        if ctype == ClauseType.AUDIT_RIGHTS:
            ev.audit_frequency_months = self._months(
                t, r"(?:audit.{0,30}frequen\w*|audit.{0,30}once|conduct.{0,20}audit)"
            )

        # ── Test coverage (type-specific — scope/SLA only, not payment) ───────
        if ctype in (ClauseType.SLA, ClauseType.SCOPE):
            ev.test_coverage_percent = self._percent(t, r"(?:test\s+coverage|unit\s+test)")

        return ev


# ─────────────────────────────────────────────────────────────────────────────
# 3. VALUE DIFF ENGINE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValueChange:
    """A single detected value-level change between two matched clauses."""
    field: str
    label: str
    old_value: Any
    new_value: Any
    old_display: str
    new_display: str
    change_pct: float | None
    direction: str          # "increased" | "decreased" | "changed" | "added" | "removed"
    severity: str
    risk_score: int
    explanation: str
    clause_type: str
    # Priority 6: enhanced finding fields
    change_category: str = ""    # "numeric" | "monetary" | "categorical" | "temporal"
    evidence: str = ""           # raw extracted snippet from clause text

    def to_evidence_string(self) -> str:
        return (
            f"{self.label}: {self.old_display} → {self.new_display} "
            f"({self.direction}, {abs(self.change_pct or 0):.0f}% change)"
        )


# Per-field metadata: (label, unit, higher_is_worse_for_client, change_category)
_FIELD_META: dict[str, tuple[str, str, bool | None, str]] = {
    "duration_months":          ("Contract Duration",        "months",   True,  "temporal"),
    "payment_days":             ("Payment Terms",            "days",     True,  "temporal"),
    "advance_percent":          ("Advance Payment",          "%",        True,  "numeric"),
    "penalty_percent":          ("Penalty Rate",             "% p.m.",   True,  "numeric"),
    "interest_rate":            ("Interest Rate",            "%",        True,  "numeric"),
    "late_payment_interest":    ("Late Payment Interest",    "%",        True,  "numeric"),
    "contract_value_inr":       ("Contract Value",           "₹",        True,  "monetary"),
    "liability_cap_inr":        ("Liability Cap",            "₹",        False, "monetary"),
    "liability_cap_months":     ("Liability Cap",            "months",   False, "temporal"),
    "notice_days":              ("Termination Notice",       "days",     False, "temporal"),
    "confidentiality_years":    ("Confidentiality Period",   "years",    False, "temporal"),
    "warranty_days":            ("Warranty Period",          "days",     False, "temporal"),
    "data_retention_days":      ("Data Retention",           "days",     None,  "temporal"),
    "sla_uptime_percent":       ("SLA Uptime",               "%",        False, "numeric"),
    "sla_response_time_hours":  ("SLA Response Time",        "hours",    True,  "temporal"),
    "test_coverage_percent":    ("Test Coverage",            "%",        False, "numeric"),
    "insurance_amount_inr":     ("Insurance Requirement",    "₹",        False, "monetary"),
    "service_credit_percent":   ("Service Credit",          "%",        False, "numeric"),
    "non_compete_months":       ("Non-Compete Duration",     "months",   True,  "temporal"),
    "non_solicitation_months":  ("Non-Solicitation Duration","months",   True,  "temporal"),
    "renewal_notice_days":      ("Renewal Opt-Out Notice",   "days",     False, "temporal"),
    "audit_frequency_months":   ("Audit Frequency",          "months",   None,  "temporal"),
}

# Severity thresholds: (relative_change_threshold, severity, risk_score)
_SEVERITY_THRESHOLDS: list[tuple[float, str, int]] = [
    (2.00, FindingSeverity.CRITICAL, 9),
    (1.00, FindingSeverity.HIGH,     7),
    (0.50, FindingSeverity.HIGH,     6),
    (0.25, FindingSeverity.MEDIUM,   5),
    (0.10, FindingSeverity.MEDIUM,   4),
    (0.0,  FindingSeverity.LOW,      3),
]

# Per-field absolute triggers that always fire regardless of % change
_ABSOLUTE_TRIGGERS: dict[str, list[tuple[str, float, str, int]]] = {
    "payment_days":           [("gt", 45, FindingSeverity.HIGH, 7),
                               ("gt", 30, FindingSeverity.MEDIUM, 5)],
    "advance_percent":        [("gt", 10, FindingSeverity.HIGH, 7)],
    "notice_days":            [("lt", 30, FindingSeverity.HIGH, 7)],
    "confidentiality_years":  [("lt", 1,  FindingSeverity.HIGH, 7)],
    "liability_cap_months":   [("lt", 6,  FindingSeverity.HIGH, 8)],
    "sla_uptime_percent":     [("lt", 99, FindingSeverity.MEDIUM, 5),
                               ("le", 95, FindingSeverity.HIGH, 7)],
    "warranty_days":          [("lt", 30, FindingSeverity.HIGH, 7)],
    "sla_response_time_hours": [("gt", 4, FindingSeverity.MEDIUM, 5),
                                ("gt", 8, FindingSeverity.HIGH, 7)],
    "non_compete_months":     [("gt", 24, FindingSeverity.HIGH, 7)],
    "non_solicitation_months":[("gt", 24, FindingSeverity.MEDIUM, 5)],
}

# Fields where the OLD side going to None is also a finding (value was removed)
_REMOVAL_IS_FINDING: set[str] = {
    "liability_cap_inr", "liability_cap_months", "notice_days",
    "confidentiality_years", "warranty_days", "sla_uptime_percent",
    "sla_response_time_hours", "insurance_amount_inr",
}


def _format_value(field: str, value: float) -> str:
    meta = _FIELD_META.get(field, ("", "", None, "numeric"))
    unit = meta[1]
    if unit == "₹":
        if value >= 1e7:
            return f"₹{value/1e7:.2f} Cr"
        if value >= 1e5:
            return f"₹{value/1e5:.2f}L"
        return f"₹{value:,.0f}"
    if unit == "months":
        return f"{value:.0f} months"
    if unit == "years":
        return f"{value:.1f} years"
    if unit == "days":
        return f"{value:.0f} days"
    if unit == "hours":
        return f"{value:.1f} hours"
    if unit in ("%", "% p.m."):
        return f"{value:.1f}%"
    return str(value)


def _pick_severity(rel_change: float) -> tuple[str, int]:
    for threshold, sev, score in _SEVERITY_THRESHOLDS:
        if rel_change > threshold:
            return sev, score
    return FindingSeverity.LOW, 3


def _build_explanation(field: str, old: Any, new: Any,
                       direction: str, higher_is_worse: bool | None) -> str:
    meta = _FIELD_META.get(field, (field, "", None, "numeric"))
    label = meta[0]

    if isinstance(old, float) and isinstance(new, float):
        old_s = _format_value(field, old)
        new_s = _format_value(field, new)
    else:
        old_s = str(old)
        new_s = str(new)

    if direction == "removed":
        return f"{label} was present in the baseline ('{old_s}') but is absent in the new version. This removal may weaken contractual protections."
    if direction == "added":
        return f"{label} was not specified in the baseline but is now set to '{new_s}'. Review whether this new value is acceptable."

    if higher_is_worse is True and direction == "increased":
        impact = "This is unfavourable — a higher value increases risk or cost for the client."
    elif higher_is_worse is False and direction == "decreased":
        impact = "This is unfavourable — a lower value weakens client protection."
    elif higher_is_worse is True and direction == "decreased":
        impact = "This is favourable — a lower value reduces risk for the client."
    elif higher_is_worse is False and direction == "increased":
        impact = "This is favourable — a higher value strengthens client protection."
    else:
        impact = "Review whether this change is acceptable."

    return f"{label} changed from {old_s} to {new_s}. {impact}"


class ValueDiffEngine:
    """
    Compares ExtractedValues from two matched clauses and returns ValueChange
    records for every material difference found.

    Priority 1: runs after text similarity scoring, so numerically different
    clauses that look nearly identical in text are never silently passed.

    Key improvements over baseline:
    - Fires on value *removal* (old has value, new does not) for critical fields
    - Absolute triggers for SLA, warranty, response time
    - change_category and evidence fields in every ValueChange
    """

    def __init__(self) -> None:
        self._extractor = ValueExtractor()

    @staticmethod
    def _clause_text(clause: dict) -> str:
        """
        Combine heading + body for extraction. The clause splitter sometimes
        places the substantive sentence in the heading (e.g. a clause whose
        first line is the operative text), so reading body_text alone can miss
        the real value. Combining both is safe because extraction is scoped by
        context hints, not position.
        """
        heading = (clause.get("heading") or "").strip()
        body = (clause.get("body_text") or "").strip()
        if heading and body and heading not in body:
            return f"{heading}\n{body}"
        return body or heading

    def diff(
        self,
        clause_a: dict,
        clause_b: dict,
        clause_type: ClauseType | None = None,
    ) -> list[ValueChange]:
        """
        Extract values from both clauses and return list of ValueChange.
        clause_a = baseline (template or proposed draft B).
        clause_b = the version being reviewed.
        """
        ctype = clause_type or ClauseType.MISCELLANEOUS
        ev_a = self._extractor.extract(self._clause_text(clause_a), ctype)
        ev_b = self._extractor.extract(self._clause_text(clause_b), ctype)
        return self._compare(ev_a, ev_b, ctype.value)

    def _compare(
        self, ev_a: ExtractedValues, ev_b: ExtractedValues, clause_type_str: str
    ) -> list[ValueChange]:
        changes: list[ValueChange] = []

        for field in _FIELD_META:
            old_val = getattr(ev_a, field, None)
            new_val = getattr(ev_b, field, None)

            if old_val is None and new_val is None:
                continue

            meta = _FIELD_META[field]
            label = meta[0]
            higher_is_worse = meta[2]
            change_cat = meta[3]

            # ── Value removed: was in baseline, now absent ─────────────────
            if old_val is not None and new_val is None:
                if field in _REMOVAL_IS_FINDING:
                    changes.append(ValueChange(
                        field=field,
                        label=label,
                        old_value=old_val,
                        new_value=None,
                        old_display=_format_value(field, old_val),
                        new_display="not specified",
                        change_pct=None,
                        direction="removed",
                        severity=FindingSeverity.HIGH,
                        risk_score=7,
                        explanation=_build_explanation(field, old_val, None, "removed", higher_is_worse),
                        clause_type=clause_type_str,
                        change_category=change_cat,
                        evidence=f"Baseline had: {_format_value(field, old_val)}; new version has no value.",
                    ))
                continue

            # ── Value added: absent in baseline, now present ───────────────
            if old_val is None and new_val is not None:
                changes.append(ValueChange(
                    field=field,
                    label=label,
                    old_value=None,
                    new_value=new_val,
                    old_display="not specified",
                    new_display=_format_value(field, new_val),
                    change_pct=None,
                    direction="added",
                    severity=FindingSeverity.MEDIUM,
                    risk_score=5,
                    explanation=_build_explanation(field, None, new_val, "added", higher_is_worse),
                    clause_type=clause_type_str,
                    change_category=change_cat,
                    evidence=f"New value introduced: {_format_value(field, new_val)}.",
                ))
                continue

            # ── Both sides have a numeric value ────────────────────────────
            if abs(old_val - new_val) < 1e-9:
                continue

            rel_change = abs(new_val - old_val) / max(abs(old_val), 1e-9)
            direction = "increased" if new_val > old_val else "decreased"

            sev, score = _pick_severity(rel_change)

            # Override severity from absolute triggers
            for op, threshold, abs_sev, abs_score in _ABSOLUTE_TRIGGERS.get(field, []):
                triggered = (
                    (op == "gt" and new_val > threshold) or
                    (op == "lt" and new_val < threshold) or
                    (op == "ge" and new_val >= threshold) or
                    (op == "le" and new_val <= threshold)
                )
                if triggered:
                    sev_order = ["critical", "high", "medium", "low", "info"]
                    if sev_order.index(abs_sev) < sev_order.index(sev):
                        sev, score = abs_sev, abs_score

            changes.append(ValueChange(
                field=field,
                label=label,
                old_value=old_val,
                new_value=new_val,
                old_display=_format_value(field, old_val),
                new_display=_format_value(field, new_val),
                change_pct=round(rel_change * 100, 1) * (1 if new_val > old_val else -1),
                direction=direction,
                severity=sev,
                risk_score=score,
                explanation=_build_explanation(field, old_val, new_val, direction, higher_is_worse),
                clause_type=clause_type_str,
                change_category=change_cat,
                evidence=(
                    f"{label}: baseline={_format_value(field, old_val)}, "
                    f"new={_format_value(field, new_val)}, "
                    f"delta={'+' if new_val > old_val else ''}{new_val - old_val:.1f} "
                    f"({'+' if rel_change > 0 else ''}{rel_change * 100:.0f}%)"
                ),
            ))

        # ── Categorical changes ──────────────────────────────────────────────
        for cat_field, cat_label, cat_severity, cat_risk in [
            ("court_city",            "Court / Jurisdiction",       FindingSeverity.HIGH,   7),
            ("governing_law",         "Governing Law",              FindingSeverity.HIGH,   8),
            ("arbitration_seat",      "Arbitration Seat",           FindingSeverity.HIGH,   7),
            ("ip_owner",              "IP Ownership",               FindingSeverity.CRITICAL, 9),
            ("indemnity_direction",   "Indemnification Direction",  FindingSeverity.CRITICAL, 9),
            ("assignment_consent",    "Assignment Consent",         FindingSeverity.MEDIUM,  5),
            ("subcontracting_consent","Subcontracting Consent",     FindingSeverity.MEDIUM,  4),
        ]:
            old_cat = getattr(ev_a, cat_field, None)
            new_cat = getattr(ev_b, cat_field, None)

            if old_cat and new_cat and old_cat.lower() != new_cat.lower():
                changes.append(ValueChange(
                    field=cat_field,
                    label=cat_label,
                    old_value=old_cat,
                    new_value=new_cat,
                    old_display=str(old_cat),
                    new_display=str(new_cat),
                    change_pct=None,
                    direction="changed",
                    severity=cat_severity,
                    risk_score=cat_risk,
                    explanation=f"{cat_label} changed from '{old_cat}' to '{new_cat}'. This is a material legal change requiring review.",
                    clause_type=clause_type_str,
                    change_category="categorical",
                    evidence=f"Old: '{old_cat}' → New: '{new_cat}'",
                ))
            elif old_cat and not new_cat and cat_field in ("court_city", "governing_law", "ip_owner", "indemnity_direction"):
                # Critical categorical field removed
                changes.append(ValueChange(
                    field=cat_field,
                    label=cat_label,
                    old_value=old_cat,
                    new_value=None,
                    old_display=str(old_cat),
                    new_display="not specified",
                    change_pct=None,
                    direction="removed",
                    severity=cat_severity,
                    risk_score=cat_risk,
                    explanation=f"{cat_label} was '{old_cat}' in baseline but is absent in the new version.",
                    clause_type=clause_type_str,
                    change_category="categorical",
                    evidence=f"Baseline had: '{old_cat}'; new version has no equivalent.",
                ))

        return changes


# ─────────────────────────────────────────────────────────────────────────────
# 4. DYNAMIC CONFIDENCE SCORER
# ─────────────────────────────────────────────────────────────────────────────

class ConfidenceScorer:
    """
    Computes a calibrated confidence score (0.0–1.0) for each finding
    based on evidence quality, not hardcoded constants.

    Evidence signals:
      - text_similarity    : how well the clause pair was matched (0.0–1.0)
      - heading_matched    : bonus if headings aligned
      - has_ooxml_changes  : tracked-change metadata present
      - value_changes      : number of structured value differences found
      - concept_matched    : semantic concept pattern triggered
      - clause_type_known  : clause was classified (not MISCELLANEOUS)
    """

    @staticmethod
    def score(
        text_similarity: float = 0.0,
        heading_matched: bool = False,
        has_ooxml_changes: bool = False,
        value_changes_count: int = 0,
        concept_matched: bool = False,
        clause_type_known: bool = True,
    ) -> float:
        base = 0.50

        # Text similarity contribution (up to +0.20)
        base += min(text_similarity * 0.20, 0.20)

        # Heading match is strong evidence (+0.10)
        if heading_matched:
            base += 0.10

        # OOXML tracked changes are ground truth (+0.12)
        if has_ooxml_changes:
            base += 0.12

        # Each extracted value change adds evidence (+0.04 each, max +0.12)
        base += min(value_changes_count * 0.04, 0.12)

        # Concept pattern matched (+0.06)
        if concept_matched:
            base += 0.06

        # Clause type not miscellaneous — classifier was confident (+0.03)
        if clause_type_known:
            base += 0.03

        return round(min(base, 0.97), 3)


# ─────────────────────────────────────────────────────────────────────────────
# 5. CONVENIENCE: enrich a finding dict with value-change evidence
# ─────────────────────────────────────────────────────────────────────────────

def build_value_change_evidence(changes: list[ValueChange]) -> str:
    """
    Format a list of ValueChange records into a human-readable evidence block
    for inclusion in finding description / reasoning_trace.
    """
    if not changes:
        return ""
    lines = ["Value-level changes detected:"]
    for vc in changes:
        lines.append(f"  • {vc.to_evidence_string()}")
    return "\n".join(lines)
