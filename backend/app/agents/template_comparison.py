"""
Agent 1: Template Comparison Agent

Compares master template (A) against proposed draft (B).

Analysis pipeline (all offline, no API keys):
  1. Noise filtering  — excludes cover pages, GSTIN/CIN, badge text
  2. Clause classification — assigns ClauseType to every clause
  3. Heading-anchored clause alignment with composite text similarity
  4. Value-level diff  — numeric/monetary/temporal value extraction + comparison
     (fires even when text similarity is above the altered threshold)
  5. Concept-level semantic detection — 30 legal concept clusters via regex
  6. Missing clause detection
  7. Dynamic confidence scoring — calibrated per-finding, not hardcoded

Upgrade path: swap ValueExtractor internals for Voyage embeddings; replace
concept patterns with Claude verification — the rest of the pipeline is stable.
"""

from __future__ import annotations

import difflib
import re
from collections import Counter
from typing import Any

from app.agents.base_agent import PROMPT_VERSION, BaseAgent
from app.agents.clause_analyzer import (
    ClauseClassifier,
    ClauseType,
    ConfidenceScorer,
    ValueDiffEngine,
    build_value_change_evidence,
)
from app.agents import suggestion_builder as sb
from app.core.constants import FindingSeverity
from app.core.logging import get_logger

logger = get_logger(__name__)

_ALTERED_THRESHOLD = 0.55   # below this → clause flagged as significantly altered
_CRITICAL_THRESHOLD = 0.25  # below this → critical severity


# ─────────────────────────────────────────────────────────────────────────────
# NOISE FILTER
# ─────────────────────────────────────────────────────────────────────────────

_NOISE_PATTERNS = [
    re.compile(r"^(?:file\s+role|upload\s+as|upload\s+this)", re.I),
    re.compile(r"^(?:company\s+master\s+template|vendor\s+proposed|gold\s+standard)", re.I),
    re.compile(r"^(?:CIN|GSTIN)\s*:", re.I),
    re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]$"),      # GSTIN
    re.compile(r"^[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$"),   # CIN
    re.compile(r"^\s*(?:DEVIATION|NOTE|EDGE\s+CASE)\s*[:—]", re.I),
    re.compile(r"^(?:⚡|📝|⚠|✓)\s*"),
    re.compile(r"^contract\s+intelligence\s+platform", re.I),
    re.compile(r"^(?:this\s+document\s+is\s+the\s+company|this\s+is\s+the\s+vendor)", re.I),
]


def _is_noise(clause: dict) -> bool:
    text    = (clause.get("body_text") or "").strip()
    heading = (clause.get("heading")   or "").strip()
    if len(text) < 15:
        return True
    for p in _NOISE_PATTERNS:
        if p.search(text) or p.search(heading):
            return True
    if re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]$", text.strip()):
        return True
    if re.match(r"^[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$", text.strip()):
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# TEXT SIMILARITY
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _ngrams(text: str, n: int = 3) -> Counter:
    words = text.split()
    return Counter(" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1)))


def _jaccard(a: str, b: str, n: int = 3) -> float:
    sa = set(_ngrams(a, n))
    sb = set(_ngrams(b, n))
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _token_overlap(a: str, b: str) -> float:
    wa = set(a.split())
    wb = set(b.split())
    return len(wa & wb) / len(wb) if wb else 0.0


def _composite_sim(text_a: str, text_b: str) -> float:
    na = _normalize(text_a)
    nb = _normalize(text_b)
    if not na or not nb:
        return 0.0
    seq = difflib.SequenceMatcher(None, na, nb).ratio()
    jac = _jaccard(na, nb)
    tok = _token_overlap(na, nb)
    return 0.40 * seq + 0.35 * jac + 0.25 * tok


def _normalize_heading(h: str) -> str:
    h = re.sub(r"^[\d\.]+\s*", "", (h or "")).strip().lower()
    return re.sub(r"\s+", " ", h)


def _best_match(clause_b: dict, clauses_a: list[dict]) -> tuple[dict | None, float, bool]:
    """Return (best_a, score, heading_matched)."""
    best_clause = None
    best_score  = -1.0
    heading_matched = False
    hb = _normalize_heading(clause_b.get("heading") or "")
    tb = (clause_b.get("body_text") or "").strip()

    for ca in clauses_a:
        ha = _normalize_heading(ca.get("heading") or "")
        ta = (ca.get("body_text") or "").strip()
        body_score = _composite_sim(ta, tb)
        hm = False
        if ha and hb:
            hs = difflib.SequenceMatcher(None, ha, hb).ratio()
            if hs >= 0.85:
                body_score = min(1.0, body_score + 0.15)
                hm = True
        if body_score > best_score:
            best_score = body_score
            best_clause = ca
            heading_matched = hm

    return best_clause, max(0.0, best_score), heading_matched


def _diff_summary(text_a: str, text_b: str) -> str:
    la = text_a.splitlines() or [text_a]
    lb = text_b.splitlines() or [text_b]
    diff = list(difflib.unified_diff(la, lb, lineterm="", n=1))
    added   = [l[1:].strip() for l in diff if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:].strip() for l in diff if l.startswith("-") and not l.startswith("---")]
    parts = []
    if removed:
        parts.append(f"Removed: \"{'; '.join(removed[:2])}\"")
    if added:
        parts.append(f"Added: \"{'; '.join(added[:2])}\"")
    return "; ".join(parts) or "Minor formatting change."


# ─────────────────────────────────────────────────────────────────────────────
# HIGH-RISK KEYWORDS
# ─────────────────────────────────────────────────────────────────────────────

_RISK_KW = [
    (r"\bindemnif\w*",                   "indemnification"),
    (r"\bliabilit\w*",                   "liability"),
    (r"\bwarrant\w*",                    "warranty"),
    (r"\bpenalt\w*",                     "penalty"),
    (r"\bterminate\b|\btermination\b",   "termination"),
    (r"\bconfidential\w*",               "confidentiality"),
    (r"\barbitrat\w*",                   "arbitration"),
    (r"\bexclusive\b",                   "exclusivity"),
    (r"\bnon[- ]?compet\w*",             "non-compete"),
    (r"\bforce\s+majeure\b",             "force majeure"),
    (r"\bintellectual\s+property\b|\bip\s+rights?\b", "intellectual property"),
    (r"\bgoverning\s+law\b",             "governing law"),
    (r"\bjurisdiction\b",                "jurisdiction"),
    (r"\bno\s+liabilit\w*|\bliability.{0,15}excluded\b", "liability exclusion"),
    (r"\bno\s+refund\b|\bnon[- ]refundable\b", "no-refund clause"),
    (r"\bauto[- ]?renew\w*\b",           "auto-renewal"),
    (r"\bnon[- ]?solicit\w*\b",          "non-solicitation"),
    (r"\bassignment\b",                  "assignment"),
    (r"\bsubcontract\w*\b",              "subcontracting"),
]


def _risk_keywords(text: str) -> list[str]:
    return [lbl for pat, lbl in _RISK_KW if re.search(pat, text, re.I)]


def _word_delta(a: str, b: str) -> tuple[int, int]:
    wa = set(_normalize(a).split())
    wb = set(_normalize(b).split())
    return len(wb - wa), len(wa - wb)


# ─────────────────────────────────────────────────────────────────────────────
# 30-CONCEPT SEMANTIC DETECTION MAP
# ─────────────────────────────────────────────────────────────────────────────

_SEMANTIC_CONCEPTS = [
    # ── 1–10: Critical commercial clauses ────────────────────────────────────
    {
        "name": "IP ownership reversed",
        "template_signals": [r"\bvest\b.{0,40}\bclient\b", r"\bclient.{0,40}\bown\b"],
        "danger_signals": [
            r"\bremain.{0,30}\bvendor\b",
            r"\bvendor.{0,30}\bretain.{0,30}\b(?:all|exclusive)\b",
            r"\bproperty\s+of\s+the\s+vendor\b",
            r"\bnon[- ]?exclusive.{0,30}licen[sc]e.{0,40}client\b",
        ],
        "severity": FindingSeverity.CRITICAL, "risk_score": 10,
        "recommendation": "IP must vest in the Client upon full payment. Vendor retaining IP means the client pays for deliverables it does not own.",
    },
    {
        "name": "Liability cap removed or unlimited",
        "template_signals": [r"\baggregate\s+liability.{0,40}\bnot\s+exceed\b"],
        "danger_signals": [
            r"\bunlimited\b.{0,30}\bliabilit\w*",
            r"\bliabilit\w*.{0,30}\bunlimited\b",
            r"\bno\s+(?:cap|limit)\s+on\b.{0,20}\bliabilit\w*",
            r"\bliabilit\w*\s+(?:shall\s+not\s+be\s+capp?ed|is\s+unlimited)\b",
        ],
        "severity": FindingSeverity.CRITICAL, "risk_score": 10,
        "recommendation": "Liability must be capped. Unlimited liability exposes the vendor to catastrophic financial risk.",
    },
    {
        "name": "Indemnification reversed",
        "template_signals": [r"\bvendor\s+shall\s+indemnif\w*\s+(?:and\s+hold\s+harmless\s+)?(?:the\s+)?client\b"],
        "danger_signals": [
            r"\bclient\s+shall\s+(?:fully\s+)?indemnif\w*\s+(?:and\s+hold\s+harmless\s+)?(?:the\s+)?vendor\b",
            r"\bclient.{0,30}\bindemnif\w*.{0,30}\bvendor\b",
            r"\bindemnif\w*.{0,40}\bvendor\s+against\b",
        ],
        "severity": FindingSeverity.CRITICAL, "risk_score": 10,
        "recommendation": "Indemnification direction is reversed. Client should NOT be indemnifying the vendor for vendor-related claims.",
    },
    {
        "name": "Jurisdiction changed",
        "template_signals": [r"\bmumbai\b.{0,50}\bexclusive\s+jurisdiction\b", r"\bexclusive\s+jurisdiction\b.{0,50}\bmumbai\b"],
        "danger_signals": [
            r"\b(?:new\s+delhi|delhi|bangalore|bengaluru|chennai|kolkata|hyderabad)\b.{0,50}\b(?:exclusive\s+jurisdiction|courts?\s+(?:at|of|in))\b",
            r"\bcourts?\s+(?:at|of|in)\s+(?:new\s+delhi|delhi|bangalore|bengaluru)\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Jurisdiction moved away from Mumbai. Affects where disputes are litigated; must be approved by legal.",
    },
    {
        "name": "Arbitration removed",
        "template_signals": [r"\barbitrat\w*\s+and\s+conciliation\s+act\b"],
        "danger_signals": [r"^(?!.*\barbitrat\w*).*(?:dispute|jurisdiction|court).*$"],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Arbitration removed. Without it, disputes go directly to court — slower and more expensive.",
    },
    {
        "name": "Confidentiality period weakened",
        "template_signals": [r"\bthree\s*\(?\s*3\s*\)?\s*years?\b.{0,60}\bconfidential\w*"],
        "danger_signals": [
            r"\bone\s*\(?\s*1\s*\)?\s*year\b.{0,60}\bconfidential\w*",
            r"\bsix\s*\(?\s*6\s*\)?\s*months?\b.{0,60}\bconfidential\w*",
            r"\bconfidential\w*.{0,60}\bone\s*\(?\s*1\s*\)?\s*year\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Confidentiality duration reduced below 3-year standard. Weakens post-termination trade-secret protection.",
    },
    {
        "name": "Termination notice reduced",
        "template_signals": [r"\bsixty\s*\(?\s*60\s*\)?\s*days?\b.{0,60}\b(?:notice|terminat\w*)\b"],
        "danger_signals": [
            r"\b(?:seven|fifteen|14|7|15)\s*\(?\s*\d*\s*\)?\s*days?\b.{0,60}\b(?:notice|terminat\w*)\b",
            r"\bterminat\w*.{0,60}\b(?:seven|fifteen|7|15)\s*(?:\(\d+\))?\s*days?\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Termination notice below 60-day standard. Insufficient wind-down time.",
    },
    {
        "name": "Payment terms extended beyond MSME limit",
        "template_signals": [r"\bthirty\s*\(?\s*30\s*\)?\s*days?\b.{0,40}\b(?:payment|invoice|pay)\b"],
        "danger_signals": [
            r"\b(?:sixty|ninety|90|60)\s*(?:\(\d+\))?\s*days?\b.{0,60}\b(?:invoice|payment|pay)\b",
            r"\b(?:payment|pay).{0,60}\b(?:sixty|ninety|90|60)\s*(?:\(\d+\))?\s*days?\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 8,
        "recommendation": "Payment terms exceed 30 days and may violate the MSME Act's 45-day limit for MSME vendors.",
    },
    {
        "name": "Auto-renewal clause inserted",
        "template_signals": [],
        "danger_signals": [r"\bautomat\w+\s+renew\w*\b", r"\bauto[- ]?renew\w*\b", r"\brenew\w*\s+automatically\b"],
        "severity": FindingSeverity.MEDIUM, "risk_score": 6,
        "recommendation": "Auto-renewal not in template. Creates lock-in risk if opt-out window is missed.",
    },
    {
        "name": "Penalty / liquidated damages clause inserted",
        "template_signals": [],
        "danger_signals": [
            r"\bpenalt\w*\s+of\s+\d+\s*%",
            r"\bliquidated\s+damages\b",
            r"\b\d+\s*%\s*per\s+(?:month|week|day)\b",
            r"\bcompounded\s+(?:monthly|daily|weekly)\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 8,
        "recommendation": "Penalty/liquidated-damages clause not in template. Review rate and enforceability under ICA Section 74.",
    },
    # ── 11–20: Operational / structural clauses ───────────────────────────────
    {
        "name": "Non-compete clause inserted",
        "template_signals": [],
        "danger_signals": [r"\bnon[- ]?compet\w+\b", r"\bnot\s+to\s+(?:carry\s+on|compet\w+)\b", r"\brefrain\s+from\s+competing\b"],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Non-compete clause not present in template. Verify enforceability under ICA Section 27 (restraint of trade is void).",
    },
    {
        "name": "Non-solicitation clause inserted",
        "template_signals": [],
        "danger_signals": [
            r"\bnon[- ]?solicit\w+\b",
            r"\bshall\s+not\s+(?:directly\s+or\s+indirectly\s+)?(?:solicit|hire|engage)\b.{0,30}\bemployee\b",
        ],
        "severity": FindingSeverity.MEDIUM, "risk_score": 5,
        "recommendation": "Non-solicitation clause inserted. Review restriction period and scope with HR/Legal.",
    },
    {
        "name": "Assignment rights removed or restricted",
        "template_signals": [r"\bmay\s+assign\b|\bassignment\s+by\s+(?:either|both)\b"],
        "danger_signals": [r"\bmay\s+not\s+assign\b|\bcannot\s+assign\b|\bno\s+assignment\b|\bprior\s+written\s+consent.{0,30}\bassign\b"],
        "severity": FindingSeverity.MEDIUM, "risk_score": 5,
        "recommendation": "Assignment clause changed. Ensure client retains ability to assign to affiliates or successors.",
    },
    {
        "name": "Subcontracting restricted",
        "template_signals": [],
        "danger_signals": [
            r"\bmay\s+not\s+subcontract\b|\bnot\s+permitted\s+to\s+subcontract\b",
            r"\bprior\s+written\s+approval.{0,30}\bsubcontract\b",
        ],
        "severity": FindingSeverity.LOW, "risk_score": 3,
        "recommendation": "Subcontracting requires prior written approval. Verify this aligns with delivery model.",
    },
    {
        "name": "Audit rights removed",
        "template_signals": [r"\bright\s+to\s+audit\b|\bmay\s+inspect\b|\baccess\s+to\s+books\b"],
        "danger_signals": [r"^(?!.*(?:audit|inspect|books\s+and\s+records)).*$"],
        "severity": FindingSeverity.MEDIUM, "risk_score": 5,
        "recommendation": "Audit rights not found in vendor draft. Client must retain right to audit vendor's compliance.",
    },
    {
        "name": "Exclusivity clause inserted",
        "template_signals": [],
        "danger_signals": [
            r"\bexclusive\s+provider\b|\bsolely\s+and\s+exclusively\b",
            r"\bshall\s+not\s+engage\s+(?:any\s+)?other\s+vendor\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Exclusivity clause not in template. This locks the client into a single vendor without competitive options.",
    },
    {
        "name": "Change of control provision missing",
        "template_signals": [r"\bchange\s+of\s+control\b"],
        "danger_signals": [r"^(?!.*change\s+of\s+control).*$"],
        "severity": FindingSeverity.LOW, "risk_score": 3,
        "recommendation": "Change of control clause not found in draft. Client should have termination right on vendor acquisition.",
    },
    {
        "name": "Warranty period weakened or removed",
        "template_signals": [r"\bwarrant\w*\b.{0,60}\bdays?\b|\bninety\s*\(?90\)?\s*days?\b.{0,30}\bwarrant\w*\b"],
        "danger_signals": [
            r"\bno\s+warrant\w*\b|\bexcluded\s+warrant\w*\b|\bwithout\s+warrant\w*\b",
            r"\b(?:as\s+is|as-is)\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Warranty removed or weakened. Vendor should warrant deliverables are defect-free for at least 90 days.",
    },
    {
        "name": "SLA / uptime commitment removed",
        "template_signals": [r"\bservice\s+level\b|\bsla\b|\buptime\b"],
        "danger_signals": [r"\bbest\s+efforts?\b|\bcommercially\s+reasonable\s+efforts?\b"],
        "severity": FindingSeverity.MEDIUM, "risk_score": 5,
        "recommendation": "'Best efforts' language replaces concrete SLA. Insist on measurable uptime/response time commitments.",
    },
    {
        "name": "Data protection weakened",
        "template_signals": [r"\bdpdp\s+act\b|\bdigital\s+personal\s+data\b"],
        "danger_signals": [
            r"\bit\s+act\s+2008\b(?!.*dpdp)",  # IT Act but no DPDP reference
            r"\breasonable\s+(?:security|measures)\b(?!.*dpdp)",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "DPDP Act 2023 reference missing. Data processing clauses must reference current Indian data protection law.",
    },
    # ── 21–30: Financial / risk clauses ──────────────────────────────────────
    {
        "name": "Insurance requirement inserted",
        "template_signals": [],
        "danger_signals": [
            r"\bshall\s+maintain\b.{0,30}\binsurance\b",
            r"\binsurance\s+coverage\b.{0,30}\b(?:shall|must)\b",
        ],
        "severity": FindingSeverity.LOW, "risk_score": 3,
        "recommendation": "Insurance requirement inserted. Verify coverage type and amount are commercially reasonable.",
    },
    {
        "name": "Governing law changed from India",
        "template_signals": [r"\bgoverned\s+by.{0,30}\blaws?\s+of\s+india\b"],
        "danger_signals": [
            r"\bgoverned\s+by.{0,30}\blaws?\s+of\s+(?!india)([A-Z][a-z]+)",
            r"\bapplicable\s+law.{0,20}\b(?!india)[A-Z][a-z]+\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 8,
        "recommendation": "Governing law changed away from India. Enforcing the contract under foreign law adds significant cost and complexity.",
    },
    {
        "name": "Force majeure notification window extended",
        "template_signals": [r"\bseven\s*\(?\s*7\s*\)?\s*days?\b.{0,30}\bforce\s+majeure\b"],
        "danger_signals": [
            r"\bforce\s+majeure\b.{0,80}\b(?:fourteen|thirty|21|30|14)\s*(?:\(\d+\))?\s*days?\b",
        ],
        "severity": FindingSeverity.LOW, "risk_score": 3,
        "recommendation": "Force majeure notification window extended beyond template's 7-day standard. Shortens response time.",
    },
    {
        "name": "Data retention obligation inserted",
        "template_signals": [],
        "danger_signals": [
            r"\bretain.{0,30}\bdata.{0,30}\b(?:years?|months?)\b",
            r"\bdata.{0,20}retention\s+period\b",
        ],
        "severity": FindingSeverity.LOW, "risk_score": 3,
        "recommendation": "Data retention period inserted. Verify it does not conflict with DPDP Act storage limitation obligations.",
    },
    {
        "name": "Service credits clause inserted",
        "template_signals": [],
        "danger_signals": [
            r"\bservice\s+credits?\b.{0,30}\bfail\w*\b",
            r"\bsla\s+credit\b|\brebate\b.{0,20}\bsla\b",
        ],
        "severity": FindingSeverity.LOW, "risk_score": 3,
        "recommendation": "Service credits clause inserted. Verify credit amounts and claim process are acceptable.",
    },
    {
        "name": "Escalation clause inserted",
        "template_signals": [],
        "danger_signals": [
            r"\bescalation\s+(?:procedure|process|path)\b",
            r"\bescalated\s+to\b.{0,30}\b(?:senior|management|board)\b",
        ],
        "severity": FindingSeverity.LOW, "risk_score": 2,
        "recommendation": "Escalation process inserted. Ensure timelines and escalation levels are aligned with governance structure.",
    },
    {
        "name": "Limitation on class actions inserted",
        "template_signals": [],
        "danger_signals": [
            r"\bclass\s+action\b|\bcollective\s+action\b|\brepresentative\s+proceeding\b",
            r"\bwaive\w*.{0,30}\bclass\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Class action waiver inserted. Enforceability under Indian law is questionable; obtain legal opinion.",
    },
    {
        "name": "No-refund clause inserted",
        "template_signals": [],
        "danger_signals": [r"\bno\s+refund\b|\bnon[- ]?refundable\b|\ball\s+sales\s+final\b"],
        "severity": FindingSeverity.MEDIUM, "risk_score": 5,
        "recommendation": "No-refund provision inserted. May conflict with Consumer Protection Act 2019 rights.",
    },
    {
        "name": "Liability for consequential damages excluded",
        "template_signals": [r"\bneither\s+party\s+shall\s+be\s+liable\b.{0,30}\bconsequential\b"],
        "danger_signals": [
            r"\bvendor\s+shall\s+not\s+be\s+liable\b.{0,30}\bconsequential\b(?!.*neither)",
            r"\bconsequential.{0,30}\bexcluded\s+in\s+favour\s+of\s+(?:the\s+)?vendor\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Consequential damage exclusion is one-sided (vendor only). Template applies it to both parties symmetrically.",
    },
    {
        "name": "Advance payment cap increased",
        "template_signals": [r"\badvance.{0,30}\bten\s*\(?\s*10\s*\)?\s*percent\b"],
        "danger_signals": [
            r"\badvance.{0,30}\b(?:twenty|thirty|forty|50|30|40)\s*(?:\(\d+\))?\s*(?:percent|%)\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Advance payment cap increased above 10% template standard. Increases upfront financial exposure.",
    },
    {
        "name": "Entire agreement clause weakened",
        "template_signals": [r"\bentire\s+agreement\b|\bsupersedes\b"],
        "danger_signals": [r"\bnotwithstanding\b.{0,40}\bentire\s+agreement\b"],
        "severity": FindingSeverity.LOW, "risk_score": 3,
        "recommendation": "Entire agreement clause has a carve-out. Ensure it does not allow hidden obligations from other documents.",
    },
    # ── 31–38: Additional concepts (Priority 4 expansion) ────────────────────
    {
        "name": "Renewal terms changed to automatic",
        "template_signals": [r"\brenew\w*\b.{0,60}\bwritten\s+notice\b|\bopt[- ]?out\b.{0,30}\brenewal\b"],
        "danger_signals": [
            r"\bautomat\w+\s+renew\w*\b.{0,60}\bno\s+(?:further\s+)?notice\b",
            r"\brunning\s+renewal\b|\bperpetuall?y\s+renew\b",
            r"\brenew\w*\s+without\s+notice\b",
        ],
        "severity": FindingSeverity.MEDIUM, "risk_score": 6,
        "recommendation": "Renewal clause changed from opt-in to automatic without notice. Negotiate an explicit opt-out window.",
    },
    {
        "name": "SLA service credits too low or uncapped",
        "template_signals": [r"\bservice\s+credit\b|\bsla\s+credit\b"],
        "danger_signals": [
            r"\bservice\s+credits?\b.{0,40}\b(?:maximum|cap|limit)\b.{0,20}\b(?:one|two|1|2)\s*%",
            r"\bservice\s+credits?\b.{0,30}\bsole\s+(?:and\s+exclusive\s+)?remedy\b",
        ],
        "severity": FindingSeverity.MEDIUM, "risk_score": 5,
        "recommendation": "Service credit cap is very low or credits are stated as the sole remedy. Negotiate meaningful credit percentages and preserve right to terminate for persistent failure.",
    },
    {
        "name": "Governing law clause absent",
        "template_signals": [r"\bgoverned\s+by.{0,30}\blaws?\s+of\s+india\b"],
        "danger_signals": [r"^(?!.*(?:governed\s+by|governing\s+law|applicable\s+law)).*$"],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Governing law clause not found. Without it, the applicable law is ambiguous and dispute resolution becomes complex.",
    },
    {
        "name": "Non-compete period unreasonably long",
        "template_signals": [],
        "danger_signals": [
            r"\bnon[- ]?compet\w+\b.{0,80}\b(?:three|four|five|6|7|8|9|10|36|48|60)\s*(?:\(\d+\))?\s*(?:years?|months?)\b",
            r"\b(?:36|48|60)\s*months?\b.{0,60}\bnon[- ]?compet\w+\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Non-compete duration exceeds reasonable limits. Periods beyond 12–24 months are likely void under ICA Section 27.",
    },
    {
        "name": "Non-solicitation scope overreach",
        "template_signals": [],
        "danger_signals": [
            r"\bshall\s+not\s+(?:directly\s+or\s+indirectly\s+)?(?:solicit|hire|engage|approach)\b.{0,60}\b(?:any\s+)?(?:client|customer|prospect)\b",
        ],
        "severity": FindingSeverity.MEDIUM, "risk_score": 5,
        "recommendation": "Non-solicitation extends to clients/customers, not just employees. This significantly limits business development; obtain legal sign-off.",
    },
    {
        "name": "Data retention obligation conflicts with DPDP Act",
        "template_signals": [],
        "danger_signals": [
            r"\bretain\b.{0,30}\bpersonal\s+data\b.{0,30}\b(?:indefinitely|perpetually|no\s+fixed\s+period)\b",
            r"\bdata\s+may\s+be\s+retained\s+(?:at\s+)?(?:vendor|provider)[\''s]*\s+discretion\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Retention obligation is indefinite or at vendor's discretion. DPDP Act 2023 requires a defined retention period with deletion obligations.",
    },
    {
        "name": "Insurance coverage inadequate or removed",
        "template_signals": [
            r"\bshall\s+maintain\b.{0,30}\binsurance\b",
            r"\bprofessional\s+indemnity\b|\berrors\s+and\s+omissions\b",
        ],
        "danger_signals": [
            r"\bno\s+insurance\s+(?:shall\s+be\s+)?required\b",
            r"\binsurance\s+(?:is\s+)?not\s+required\b",
            r"\bat\s+(?:vendor|provider)[\''s]*\s+(?:own\s+)?discretion\b.{0,30}\binsurance\b",
        ],
        "severity": FindingSeverity.MEDIUM, "risk_score": 5,
        "recommendation": "Insurance requirement removed or made optional. Minimum professional indemnity and general liability cover should be mandatory.",
    },
    {
        "name": "Audit rights scope narrowed",
        "template_signals": [r"\bright\s+to\s+audit\b|\bmay\s+inspect\b|\baccess\s+to\s+books\b"],
        "danger_signals": [
            r"\baudit\b.{0,80}\b(?:one|once|1)\s+(?:time|occasion)\b.{0,40}\bterm\b",
            r"\baudit\b.{0,80}\b(?:third[- ]party\s+auditor|independent\s+auditor)\b.{0,40}\bonly\b",
            r"\baudit\b.{0,50}\bnot\s+more\s+than\s+(?:once|one)\b",
        ],
        "severity": FindingSeverity.MEDIUM, "risk_score": 5,
        "recommendation": "Audit rights are significantly narrowed (frequency limited or third-party auditor only). Negotiate annual or reasonable-cause audit rights.",
    },
    {
        "name": "Exclusivity prevents multi-vendor strategy",
        "template_signals": [],
        "danger_signals": [
            r"\bshall\s+not\s+engage\b.{0,50}\bcompeting\s+(?:vendor|provider|supplier)\b",
            r"\bexclusive\w*\s+engagement\b.{0,50}\bvendor\b",
            r"\bexclusivity\s+period\b|\bduring\s+the\s+exclusivity\b",
        ],
        "severity": FindingSeverity.HIGH, "risk_score": 7,
        "recommendation": "Exclusivity clause prevents engaging competing vendors. This creates lock-in and eliminates leverage. Ensure adequate compensation or remove.",
    },
]


def _detect_semantic(clause_b: dict, clauses_a: list[dict]) -> list[dict]:
    tb = (clause_b.get("body_text") or "").lower()
    full_a = " ".join((c.get("body_text") or "") for c in clauses_a).lower()
    hits: list[dict] = []

    for concept in _SEMANTIC_CONCEPTS:
        template_establishes = any(
            re.search(s, full_a, re.I) for s in concept["template_signals"]
        ) if concept["template_signals"] else False

        b_danger = any(re.search(s, tb, re.I | re.MULTILINE) for s in concept["danger_signals"])
        if not b_danger:
            continue

        if not concept["template_signals"] or template_establishes:
            hits.append({
                "concept":        concept["name"],
                "severity":       concept["severity"],
                "risk_score":     concept["risk_score"],
                "recommendation": concept["recommendation"],
                "is_insertion":   not bool(concept["template_signals"]),
            })

    return hits


# ─────────────────────────────────────────────────────────────────────────────
# AGENT
# ─────────────────────────────────────────────────────────────────────────────

class TemplateComparisonAgent(BaseAgent):
    name = "template_comparison"

    def __init__(self) -> None:
        super().__init__()
        self._diff_engine = ValueDiffEngine()

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        project_id = context["project_id"]
        tenant_id  = context["tenant_id"]
        clauses_a  = context.get("clauses_a", [])
        clauses_b  = context.get("clauses_b", [])

        self._log_run_start(project_id, tenant_id)

        # ── Classify all clauses ──────────────────────────────────────────
        clauses_a = ClauseClassifier.classify_all(clauses_a)
        clauses_b = ClauseClassifier.classify_all(clauses_b)

        findings: list[dict] = []
        matched_a_ids: set[str] = set()

        # ── Step 1: scan B clauses ─────────────────────────────────────────
        for cb in clauses_b:
            if _is_noise(cb):
                continue
            tb = (cb.get("body_text") or "").strip()
            if len(tb) < 20:
                continue

            ctype_str = cb.get("clause_type", ClauseType.MISCELLANEOUS.value)
            try:
                ctype = ClauseType(ctype_str)
            except ValueError:
                ctype = ClauseType.MISCELLANEOUS

            best_a, score, heading_matched = _best_match(cb, clauses_a)

            # ── New clause (no match in template) ─────────────────────────
            if best_a is None or score < 0.10:
                risk_kws = _risk_keywords(tb)
                sev = FindingSeverity.HIGH if risk_kws else FindingSeverity.MEDIUM
                conf = ConfidenceScorer.score(
                    text_similarity=score,
                    heading_matched=heading_matched,
                    clause_type_known=(ctype != ClauseType.MISCELLANEOUS),
                )
                findings.append(self._build_finding(
                    flag_type="clause_added",
                    severity=sev,
                    title=f"New clause in draft (not in template): {cb.get('heading') or ctype_str}",
                    description=(
                        f"[Clause Type: {ctype_str}] "
                        f"This clause appears in the proposed draft but has no equivalent in the master template "
                        f"(best match: {score:.0%}). "
                        + (f"Risk keywords: {', '.join(risk_kws)}." if risk_kws else "")
                    ),
                    recommendation="Review whether this clause aligns with company policy and should be accepted.",
                    source_clause_id=str(cb.get("id", "")),
                    confidence=conf,
                    reasoning_trace=f"clause_type={ctype_str}; no_template_match; best_score={score:.3f}",
                    risk_score=7 if risk_kws else 4,
                    clause_type=ctype_str,
                    priority=sb.priority_for(sev),
                ))
                continue

            matched_a_ids.add(str(best_a.get("id", "")))

            # ── Value-level diff (runs even when text similarity is high) ──
            value_changes = self._diff_engine.diff(best_a, cb, ctype)

            for vc in value_changes:
                vc_conf = ConfidenceScorer.score(
                    text_similarity=score,
                    heading_matched=heading_matched,
                    has_ooxml_changes=bool(cb.get("has_tracked_insertion") or cb.get("has_tracked_deletion")),
                    value_changes_count=1,
                    clause_type_known=(ctype != ClauseType.MISCELLANEOUS),
                )
                findings.append(self._build_finding(
                    flag_type="template_deviation",
                    severity=vc.severity,
                    title=f"[Value Change] {vc.label}: {vc.old_display} → {vc.new_display}",
                    description=(
                        f"[Clause Type: {vc.clause_type}] "
                        f"{vc.explanation} "
                        f"Text similarity to template clause '{best_a.get('heading') or 'Untitled'}': {score:.0%}."
                    ),
                    recommendation=f"Review this change carefully. {vc.explanation}",
                    source_clause_id=str(cb.get("id", "")),
                    confidence=vc_conf,
                    reasoning_trace=(
                        f"clause_type={vc.clause_type}; "
                        f"field={vc.field}; "
                        f"old={vc.old_value}; new={vc.new_value}; "
                        f"change_pct={vc.change_pct}%; "
                        f"text_similarity={score:.3f}; heading_matched={heading_matched}"
                    ),
                    risk_score=vc.risk_score,
                    clause_type=vc.clause_type,
                    value_changes=[{
                        "field": vc.field,
                        "label": vc.label,
                        "old_value": vc.old_value,
                        "new_value": vc.new_value,
                        "old_display": vc.old_display,
                        "new_display": vc.new_display,
                        "change_pct": vc.change_pct,
                        "direction": vc.direction,
                        "severity": vc.severity,
                        "risk_score": vc.risk_score,
                        "change_category": vc.change_category,
                        "evidence": vc.evidence,
                        "explanation": vc.explanation,
                    }],
                    suggestion=sb.for_value_change(vc, basis="template").as_dict(),
                    priority=sb.priority_for(vc.severity),
                ))

            # ── Text-similarity deviation ──────────────────────────────────
            if score < _ALTERED_THRESHOLD:
                diff_note = _diff_summary(best_a.get("body_text", ""), tb)
                risk_kws  = _risk_keywords(tb)
                added_w, removed_w = _word_delta(best_a.get("body_text", ""), tb)

                if score < _CRITICAL_THRESHOLD:
                    sev, rs = FindingSeverity.CRITICAL, 9
                elif risk_kws:
                    sev, rs = FindingSeverity.HIGH, 7
                else:
                    sev, rs = FindingSeverity.MEDIUM, 5

                conf = ConfidenceScorer.score(
                    text_similarity=score,
                    heading_matched=heading_matched,
                    has_ooxml_changes=bool(cb.get("has_tracked_insertion") or cb.get("has_tracked_deletion")),
                    value_changes_count=len(value_changes),
                    clause_type_known=(ctype != ClauseType.MISCELLANEOUS),
                )

                evidence_block = build_value_change_evidence(value_changes)
                desc = (
                    f"[Clause Type: {ctype_str}] "
                    f"Text similarity to template clause '{best_a.get('heading') or 'Untitled'}': {score:.0%}. "
                    f"{diff_note} "
                    f"Word delta: +{added_w} added, -{removed_w} removed."
                    + (f" Risk keywords: {', '.join(risk_kws)}." if risk_kws else "")
                    + (f"\n{evidence_block}" if evidence_block else "")
                )

                findings.append(self._build_finding(
                    flag_type="template_deviation",
                    severity=sev,
                    title=f"Clause altered vs. template: {cb.get('heading') or ctype_str}",
                    description=desc,
                    recommendation=(
                        "Compare this clause against the template version. "
                        "Ensure deviations are intentional and legally reviewed."
                    ),
                    source_clause_id=str(cb.get("id", "")),
                    confidence=conf,
                    reasoning_trace=(
                        f"clause_type={ctype_str}; composite_sim={score:.3f}; "
                        f"matched_template='{best_a.get('heading')}'; "
                        f"added_words={added_w}; removed_words={removed_w}; "
                        f"value_changes={len(value_changes)}"
                    ),
                    risk_score=rs,
                    clause_type=ctype_str,
                    value_changes=[{
                        "field": vc.field,
                        "label": vc.label,
                        "old_value": vc.old_value,
                        "new_value": vc.new_value,
                        "old_display": vc.old_display,
                        "new_display": vc.new_display,
                        "change_pct": vc.change_pct,
                        "direction": vc.direction,
                        "severity": vc.severity,
                        "risk_score": vc.risk_score,
                        "change_category": vc.change_category,
                        "evidence": vc.evidence,
                        "explanation": vc.explanation,
                    } for vc in value_changes] if value_changes else [],
                    # No value-change suggestion here: each concrete value change
                    # already produces its own dedicated "[Value Change]" finding
                    # with a precise suggestion. Attaching value_changes[0] to this
                    # broad text-deviation finding risks a cross-field mismatch.
                    priority=sb.priority_for(sev),
                ))

        # ── Step 1b: semantic concept scan ────────────────────────────────
        semantic_seen: set[str] = set()
        for cb in clauses_b:
            if _is_noise(cb):
                continue
            tb = (cb.get("body_text") or "").strip()
            if len(tb) < 20:
                continue
            for sem in _detect_semantic(cb, clauses_a):
                key = sem["concept"]
                if key in semantic_seen:
                    continue
                semantic_seen.add(key)
                action = "inserted (not in template)" if sem["is_insertion"] else "deviated from template"
                conf = ConfidenceScorer.score(concept_matched=True, clause_type_known=True)
                ctype_sem = cb.get("clause_type", ClauseType.MISCELLANEOUS.value)
                findings.append(self._build_finding(
                    flag_type="template_deviation",
                    severity=sem["severity"],
                    title=f"[Semantic] {key} — {action}",
                    description=(
                        f"Concept-level analysis: '{key}' violation detected. "
                        f"This finding is based on the legal meaning of the clause, not wording similarity. "
                        f"Clause excerpt: \"{tb[:200]}{'...' if len(tb) > 200 else ''}\""
                    ),
                    recommendation=sem["recommendation"],
                    source_clause_id=str(cb.get("id", "")),
                    confidence=conf,
                    reasoning_trace=f"semantic_concept='{key}'; action='{action}'; clause='{cb.get('heading')}'",
                    risk_score=sem["risk_score"],
                    clause_type=ctype_sem,
                    suggestion=sb.for_concept(
                        concept_name=key,
                        recommendation=sem["recommendation"],
                        excerpt=tb,
                        severity=sem["severity"],
                    ).as_dict(),
                    priority=sb.priority_for(sem["severity"]),
                ))

        # ── Step 2: missing template clauses ──────────────────────────────
        for ca in clauses_a:
            if _is_noise(ca):
                continue
            ta = (ca.get("body_text") or "").strip()
            if len(ta) < 20:
                continue
            if str(ca.get("id", "")) in matched_a_ids:
                continue
            ctype_str = ca.get("clause_type", ClauseType.MISCELLANEOUS.value)
            _, score, heading_matched = _best_match(ca, clauses_b)
            if score < _ALTERED_THRESHOLD:
                risk_kws = _risk_keywords(ta)
                conf = ConfidenceScorer.score(
                    text_similarity=score,
                    heading_matched=heading_matched,
                    clause_type_known=(ctype_str != ClauseType.MISCELLANEOUS.value),
                )
                findings.append(self._build_finding(
                    flag_type="clause_missing",
                    severity=FindingSeverity.HIGH,
                    title=f"Template clause missing from draft: {ca.get('heading') or ctype_str}",
                    description=(
                        f"[Clause Type: {ctype_str}] "
                        f"This template clause is absent or substantially removed from the proposed draft "
                        f"(best match in B: {score:.0%})."
                        + (f" Risk keywords present: {', '.join(risk_kws)}." if risk_kws else "")
                    ),
                    recommendation="Confirm whether this clause was intentionally omitted; if not, re-add from the template.",
                    source_clause_id=str(ca.get("id", "")),
                    confidence=conf,
                    reasoning_trace=f"clause_type={ctype_str}; best_match_in_B={score:.3f}; below_threshold={_ALTERED_THRESHOLD}",
                    risk_score=7 if risk_kws else 6,
                    clause_type=ctype_str,
                    suggestion=sb.for_missing_clause(
                        clause_heading=ca.get("heading"),
                        template_body=ta,
                        severity=FindingSeverity.HIGH,
                    ).as_dict(),
                    priority=sb.priority_for(FindingSeverity.HIGH),
                ))

        self._log_run_complete(project_id, len(findings))

        return {
            "findings": findings,
            "token_usage": {"input_tokens": 0, "output_tokens": 0},
            "model_version": "python-composite-v2-with-value-diff",
            "prompt_version": PROMPT_VERSION,
        }
