"""
Agent 3: Indian Law Validator (demo mode — no API keys required)

Uses a bundled set of Indian contract law rules expressed as regex patterns.
Covers: Indian Contract Act 1872, IT Act 2000, MSME Act 2006, Consumer
Protection Act 2019, and key Maharashtra-specific provisions.

Each rule checks a contract clause for the presence (or absence) of legally
required or prohibited patterns and emits a finding if the rule fires.
"""

import re
from typing import Any

from app.agents.base_agent import PROMPT_VERSION, BaseAgent
from app.core.constants import FindingSeverity
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Bundled Indian law rule definitions
#
# Each rule dict:
#   id             : unique identifier
#   pattern        : regex to match against clause text (IGNORECASE)
#   match_means    : "violation" if match → finding, "required" if absence → finding
#   severity       : critical / high / medium / low
#   title          : short finding title
#   act_name       : applicable Indian statute
#   section        : section reference
#   law_text       : brief excerpt of the relevant statutory provision
#   jurisdiction   : "india" or "maharashtra"
#   recommendation : remediation suggestion
#   check_full_text: if True, "required" rules check the full contract text
#                    rather than individual clauses (default True)
# ---------------------------------------------------------------------------
_RULES: list[dict] = [
    # ── Indian Contract Act 1872 ──────────────────────────────────────────────
    {
        "id": "ICA_23_unlawful_object",
        "pattern": r"\b(illegal|unlawful|prohibited by law|against public policy|in contravention of)\b",
        "match_means": "violation",
        "severity": FindingSeverity.CRITICAL,
        "title": "Potentially unlawful object or consideration",
        "act_name": "Indian Contract Act, 1872",
        "section": "Section 23",
        "law_text": (
            "Section 23: The consideration or object of an agreement is lawful, unless it is "
            "forbidden by law, or is of such a nature that, if permitted, it would defeat the "
            "provisions of any law, or is fraudulent, or involves injury to the person or property "
            "of another, or the court regards it as immoral, or opposed to public policy."
        ),
        "jurisdiction": "india",
        "recommendation": "Remove or revise any clause that references unlawful activity or objects against public policy.",
    },
    {
        "id": "ICA_27_restraint_of_trade",
        "pattern": r"\b(restraint of trade|non[- ]?compet\w*|not to carry on|shall not engage in|refrain from competing)\b",
        "match_means": "violation",
        "severity": FindingSeverity.HIGH,
        "title": "Restraint of trade / non-compete clause detected",
        "act_name": "Indian Contract Act, 1872",
        "section": "Section 27",
        "law_text": (
            "Section 27: Every agreement by which any one is restrained from exercising a lawful "
            "profession, trade or business of any kind, is to that extent void. Exception: sale of "
            "goodwill — seller may agree not to carry on similar business within specified local limits."
        ),
        "jurisdiction": "india",
        "recommendation": (
            "Non-compete clauses are broadly void under Indian law. "
            "Limit any restriction to sale-of-goodwill scenarios or seek legal advice."
        ),
    },
    {
        "id": "ICA_74_liquidated_damages",
        "pattern": r"\b(penalty|liquidated damages|pre[- ]?determined damages|damages shall be|agreed damages)\b",
        "match_means": "violation",
        "severity": FindingSeverity.MEDIUM,
        "title": "Liquidated damages / penalty clause",
        "act_name": "Indian Contract Act, 1872",
        "section": "Section 74",
        "law_text": (
            "Section 74: When a contract has been broken, if a sum is named in the contract as the "
            "amount to be paid in case of such breach, or if the contract contains any other "
            "stipulation by way of penalty, the party complaining of the breach is entitled, whether "
            "or not actual damage or loss is proved to have been caused, to receive reasonable "
            "compensation not exceeding the amount so named or the penalty stipulated for."
        ),
        "jurisdiction": "india",
        "recommendation": (
            "Ensure any penalty clause reflects reasonable compensation, not a punitive amount. "
            "Courts will cap recovery to actual damages regardless of the figure stated."
        ),
    },
    {
        "id": "ICA_25_oral_agreement",
        "pattern": r"\b(oral agreement|verbal agreement|orally agreed|oral understanding)\b",
        "match_means": "violation",
        "severity": FindingSeverity.HIGH,
        "title": "Oral agreement reference in written contract",
        "act_name": "Indian Contract Act, 1872",
        "section": "Section 25 / Entire Agreement Principle",
        "law_text": (
            "While oral contracts can be valid, referencing prior oral agreements in a written "
            "contract creates ambiguity and may be unenforceable. Entire-agreement clauses are "
            "recommended to avoid disputes over oral representations."
        ),
        "jurisdiction": "india",
        "recommendation": "Include an entire-agreement clause stating this document supersedes all prior oral understandings.",
    },
    {
        "id": "ICA_56_impossibility",
        "pattern": r"\b(impossible|impossibility of performance|frustrated|frustration of contract)\b",
        "match_means": "violation",
        "severity": FindingSeverity.MEDIUM,
        "title": "Impossibility / frustration of contract clause",
        "act_name": "Indian Contract Act, 1872",
        "section": "Section 56",
        "law_text": (
            "Section 56: An agreement to do an act impossible in itself is void. "
            "A contract becomes void when, after execution, performance becomes impossible "
            "or unlawful due to an event the promisor could not prevent."
        ),
        "jurisdiction": "india",
        "recommendation": "Supplement impossibility references with an explicit force majeure clause listing qualifying events.",
    },
    # ── Governing Law & Dispute Resolution ─────────────────────────────────────
    {
        "id": "GOV_LAW_missing",
        "pattern": r"\b(governing law|applicable law|laws of india|jurisdiction of|subject to the laws|courts? of)\b",
        "match_means": "required",
        "severity": FindingSeverity.HIGH,
        "title": "No governing law clause detected",
        "act_name": "Indian Contract Act, 1872 / Civil Procedure Code, 1908",
        "section": "General Principle",
        "law_text": (
            "Every commercial contract should specify the governing law and jurisdiction. "
            "In India, courts apply the law of the place where the contract was made or is to be "
            "performed unless a governing law clause specifies otherwise."
        ),
        "jurisdiction": "india",
        "recommendation": "Add a governing law clause specifying Indian law and jurisdiction (e.g., Mumbai courts).",
        "check_full_text": True,
    },
    {
        "id": "ARBITRATION_act",
        "pattern": r"\b(arbitrat\w*|arbitration and conciliation act|dispute resolution|mediat\w*)\b",
        "match_means": "required",
        "severity": FindingSeverity.MEDIUM,
        "title": "No dispute resolution clause detected",
        "act_name": "Arbitration and Conciliation Act, 1996",
        "section": "Section 7",
        "law_text": (
            "Section 7: An arbitration agreement shall be in writing. "
            "A dispute resolution clause should clearly specify the arbitration seat, "
            "number of arbitrators, and governing rules."
        ),
        "jurisdiction": "india",
        "recommendation": (
            "Add a dispute resolution clause referencing the Arbitration and Conciliation Act, 1996, "
            "with Mumbai as the seat of arbitration."
        ),
        "check_full_text": True,
    },
    {
        "id": "ARBITRATION_act_wrong_name",
        "pattern": r"\bArbitration Act,?\s+1996\b",
        "match_means": "violation",
        "severity": FindingSeverity.LOW,
        "title": "Incorrect statute name: should be 'Arbitration and Conciliation Act, 1996'",
        "act_name": "Arbitration and Conciliation Act, 1996",
        "section": "Title",
        "law_text": (
            "The correct full name of the statute is 'Arbitration and Conciliation Act, 1996'. "
            "Citing it as 'Arbitration Act, 1996' (without 'and Conciliation') is technically incorrect "
            "and may create ambiguity in enforcement proceedings."
        ),
        "jurisdiction": "india",
        "recommendation": "Replace 'Arbitration Act, 1996' with 'Arbitration and Conciliation Act, 1996' throughout the document.",
    },
    # ── Payment Terms ────────────────────────────────────────────────────────────
    {
        "id": "PAYMENT_excess_90_days",
        "pattern": r"\b(?:90|ninety)\s*(?:calendar\s+)?days?\b.{0,60}\b(?:invoice|payment|due)\b"
                   r"|\b(?:invoice|payment|due)\b.{0,60}\b(?:90|ninety)\s*(?:calendar\s+)?days?\b",
        "match_means": "violation",
        "severity": FindingSeverity.HIGH,
        "title": "Payment terms exceed 90 days — unusually long credit period",
        "act_name": "Indian Contract Act, 1872 / MSME Act, 2006",
        "section": "General Commercial Practice",
        "law_text": (
            "Payment terms exceeding 90 days are commercially unusual in Indian contracts and may "
            "violate MSME Act obligations (45-day cap for MSME suppliers). Courts have struck down "
            "unreasonable credit periods as unconscionable."
        ),
        "jurisdiction": "india",
        "recommendation": "Reduce payment terms to 30–45 days. If dealing with MSME suppliers, the maximum is 45 days.",
    },
    {
        "id": "MSME_payment_over_45_days",
        "pattern": (
            r"\b(?:60|seventy|80|eighty|ninety|90|120|one\s+hundred)\s*"
            r"(?:calendar\s+)?days?\b.{0,80}\b(?:invoice|payment|due|credit)\b"
            r"|\b(?:invoice|payment|due|credit)\b.{0,80}\b"
            r"(?:60|seventy|80|eighty|ninety|90|120|one\s+hundred)\s*(?:calendar\s+)?days?\b"
        ),
        "match_means": "violation",
        "severity": FindingSeverity.HIGH,
        "title": "Payment terms likely exceed MSME 45-day limit",
        "act_name": "Micro, Small and Medium Enterprises Development Act, 2006",
        "section": "Section 15",
        "law_text": (
            "Section 15: Where any supplier supplies goods or renders services to any buyer, "
            "the buyer shall make payment on or before the date agreed upon in writing, provided "
            "the period of credit extended shall not exceed 45 days from acceptance of goods/services. "
            "Delayed payment attracts compound interest at three times the RBI bank rate."
        ),
        "jurisdiction": "india",
        "recommendation": (
            "Ensure payment terms do not exceed 45 days if contracting with an MSME supplier. "
            "Specify whether supplier qualifies as MSME or include a representation clause."
        ),
    },
    # ── IT Act 2000 ───────────────────────────────────────────────────────────────
    {
        "id": "IT_ACT_data_protection",
        "pattern": r"\b(personal (?:data|information)|sensitive personal (?:data|information)|SPDI|data protection|privacy policy)\b",
        "match_means": "violation",
        "severity": FindingSeverity.HIGH,
        "title": "Personal data clause — IT Act & DPDP compliance required",
        "act_name": "Information Technology Act, 2000 / Digital Personal Data Protection Act, 2023",
        "section": "Section 43A IT Act / Section 4 DPDP Act",
        "law_text": (
            "Section 43A IT Act: A body corporate possessing, dealing or handling any sensitive "
            "personal data or information shall be liable to pay damages by way of compensation "
            "to the person so affected. The DPDP Act 2023 additionally requires consent, "
            "data minimisation, and breach notification within 72 hours."
        ),
        "jurisdiction": "india",
        "recommendation": (
            "Include a data protection clause referencing IT Act 2000 and DPDP Act 2023. "
            "Specify consent mechanisms, data retention limits, and breach notification obligations."
        ),
    },
    {
        "id": "IT_ACT_electronic_contract",
        "pattern": r"\b(electronic signature|digital signature|e[- ]?sign|electronically sign)\b",
        "match_means": "violation",
        "severity": FindingSeverity.LOW,
        "title": "Electronic signature clause — IT Act validity check",
        "act_name": "Information Technology Act, 2000",
        "section": "Section 5 / Section 10A",
        "law_text": (
            "Section 5 & 10A: Electronic contracts and electronic signatures are valid under Indian law. "
            "However, certain documents (wills, negotiable instruments, real estate transactions) "
            "are exempt and require physical signatures."
        ),
        "jurisdiction": "india",
        "recommendation": "Confirm this contract type is eligible for electronic execution under IT Act 2000.",
    },
    # ── Stamp Duty (Maharashtra) ──────────────────────────────────────────────────
    {
        "id": "MAHA_STAMP_agreement",
        "pattern": r"\b(stamp duty|duly stamped|notarized|executed on stamp paper|e-stamp|franking)\b",
        "match_means": "required",
        "severity": FindingSeverity.MEDIUM,
        "title": "No stamp duty reference in contract",
        "act_name": "Maharashtra Stamp Act, 1958",
        "section": "Schedule I",
        "law_text": (
            "Agreements relating to immovable property, arbitration, or high-value service contracts "
            "in Maharashtra are subject to stamp duty under the Maharashtra Stamp Act, 1958. "
            "An unstamped instrument may be impounded and rendered inadmissible in court."
        ),
        "jurisdiction": "maharashtra",
        "recommendation": (
            "Verify the applicable stamp duty for this agreement category and ensure the "
            "contract is executed on properly stamped paper or e-stamped as per Maharashtra rules."
        ),
        "check_full_text": True,
    },
    # ── Confidentiality ──────────────────────────────────────────────────────────
    {
        "id": "CONF_missing",
        "pattern": r"\b(confidential\w*|non[- ]?disclosure|NDA|proprietary information|trade secret)\b",
        "match_means": "required",
        "severity": FindingSeverity.MEDIUM,
        "title": "No confidentiality / NDA clause detected",
        "act_name": "Indian Contract Act, 1872",
        "section": "General Principle",
        "law_text": (
            "Commercial contracts involving exchange of business information, pricing, or technology "
            "should include confidentiality obligations on both parties to protect trade secrets and "
            "proprietary information. Breach of confidence is actionable under common law principles "
            "adopted in India."
        ),
        "jurisdiction": "india",
        "recommendation": "Add a confidentiality clause defining protected information, obligations, and duration.",
        "check_full_text": True,
    },
    {
        "id": "CONF_duration_short",
        "pattern": r"\bconfidential\w*.{0,100}\b(1|one)\s+year\b",
        "match_means": "violation",
        "severity": FindingSeverity.LOW,
        "title": "Confidentiality duration appears short (1 year)",
        "act_name": "Indian Contract Act, 1872",
        "section": "General Principle",
        "law_text": (
            "Industry standard for confidentiality obligations in service contracts is 3–5 years. "
            "A 1-year confidentiality window may be insufficient to protect business information "
            "that has a longer commercial life."
        ),
        "jurisdiction": "india",
        "recommendation": "Consider extending the confidentiality period to at least 3 years post-termination.",
    },
    # ── Force Majeure ─────────────────────────────────────────────────────────────
    {
        "id": "FM_missing",
        "pattern": r"\b(force majeure|act of god|circumstances beyond.{0,20}control|vis major|pandemic|natural disaster)\b",
        "match_means": "required",
        "severity": FindingSeverity.LOW,
        "title": "No force majeure clause detected",
        "act_name": "Indian Contract Act, 1872",
        "section": "Section 56",
        "law_text": (
            "Section 56: An agreement to do an act impossible in itself is void. "
            "A contract to do an act which, after the contract is made, becomes impossible, or, "
            "by reason of some event which the promisor could not prevent, unlawful, becomes void "
            "when the act becomes impossible or unlawful. "
            "An explicit force majeure clause clarifies which events trigger relief."
        ),
        "jurisdiction": "india",
        "recommendation": (
            "Add a force majeure clause listing qualifying events (pandemic, natural disaster, "
            "government action) and specifying obligations to notify and mitigate."
        ),
        "check_full_text": True,
    },
    # ── Termination ───────────────────────────────────────────────────────────────
    {
        "id": "TERM_missing",
        "pattern": r"\b(terminat\w*|cancel\w*|rescind\w*|notice\s+of\s+termination)\b",
        "match_means": "required",
        "severity": FindingSeverity.MEDIUM,
        "title": "No termination clause detected",
        "act_name": "Indian Contract Act, 1872",
        "section": "Section 39",
        "law_text": (
            "Section 39: When a party to a contract has refused to perform, or disabled himself "
            "from performing, his promise in its entirety, the promisee may put an end to the "
            "contract. Termination provisions should specify clear notice periods and cure rights."
        ),
        "jurisdiction": "india",
        "recommendation": (
            "Ensure termination clauses specify: (a) minimum notice period (typically 30–90 days), "
            "(b) right to cure for non-material breach, (c) consequences upon termination including "
            "payment of dues and return of materials."
        ),
        "check_full_text": True,
    },
    {
        "id": "TERM_no_notice_period",
        "pattern": r"\bterminat\w*.{0,200}\bnotice\b",
        "match_means": "required",
        "severity": FindingSeverity.MEDIUM,
        "title": "Termination clause lacks explicit notice period",
        "act_name": "Indian Contract Act, 1872",
        "section": "Section 39",
        "law_text": (
            "Termination without adequate notice can be challenged as wrongful termination. "
            "Indian courts have upheld the requirement for reasonable notice even where contracts "
            "are silent, but specifying a period in the contract avoids disputes."
        ),
        "jurisdiction": "india",
        "recommendation": "Explicitly state the minimum notice period (recommended: 30–90 days) in the termination clause.",
        "check_full_text": False,
    },
    # ── Intellectual Property ─────────────────────────────────────────────────────
    {
        "id": "IP_assignment",
        "pattern": r"\b(intellectual property|copyright|patent|trademark|IP rights?)\b.{0,80}\b(assign\w*|transfer\w*|vest\w*)\b",
        "match_means": "violation",
        "severity": FindingSeverity.HIGH,
        "title": "IP assignment clause detected",
        "act_name": "Copyright Act, 1957 / Patents Act, 1970",
        "section": "Copyright Act Section 19 / Patents Act Section 68",
        "law_text": (
            "Copyright Act Section 19: Assignment of copyright shall be in writing signed by the "
            "assignor or his duly authorized agent. "
            "Patents Act Section 68: An assignment of a patent shall not be valid unless the same "
            "were in writing and the agreement between the parties concerned is reduced to the form "
            "of a document embodying all the terms and conditions governing their rights and "
            "obligations and duly executed."
        ),
        "jurisdiction": "india",
        "recommendation": (
            "Ensure IP assignment is explicit, written, and limited to the necessary scope. "
            "Specify whether assignment is exclusive/non-exclusive, territories covered, and consideration paid."
        ),
    },
    {
        "id": "IP_work_for_hire",
        "pattern": r"\b(work for hire|work[- ]made[- ]for[- ]hire|works created.{0,30}shall vest)\b",
        "match_means": "violation",
        "severity": FindingSeverity.MEDIUM,
        "title": "Work-for-hire clause — verify IP vesting",
        "act_name": "Copyright Act, 1957",
        "section": "Section 17",
        "law_text": (
            "Section 17: In the case of a work made by an author in the course of his employment "
            "under a contract of service or apprenticeship, the employer shall, in the absence of "
            "any agreement to the contrary, be the first owner of copyright therein."
        ),
        "jurisdiction": "india",
        "recommendation": "Explicitly state that IP created during the engagement vests in the commissioning party, with assignment in writing.",
    },
    # ── Consumer Protection ───────────────────────────────────────────────────────
    {
        "id": "CPA_unfair_terms",
        "pattern": r"\b(no refund|non[- ]?refundable|all sales final|no liability whatsoever|liability.{0,20}excluded)\b",
        "match_means": "violation",
        "severity": FindingSeverity.HIGH,
        "title": "Potentially unfair contract term (Consumer Protection Act)",
        "act_name": "Consumer Protection Act, 2019",
        "section": "Section 2(46) / Section 47",
        "law_text": (
            "Section 2(46): 'Unfair contract' means a contract between a manufacturer or trader or "
            "service provider on one hand, and a consumer on the other, having such terms which cause "
            "significant change in the rights of such consumer, including terms requiring unreasonable "
            "deposit of security, unilateral termination without reasonable cause, etc."
        ),
        "jurisdiction": "india",
        "recommendation": (
            "Review blanket liability exclusions and no-refund clauses. "
            "Consumer-facing contracts must not contain unfair terms under the CPA 2019."
        ),
    },
    # ── Entire Agreement / Merger Clause ─────────────────────────────────────────
    {
        "id": "MERGER_CLAUSE_missing",
        "pattern": r"\b(entire agreement|whole agreement|supersede[sd]?.{0,40}prior|merger clause)\b",
        "match_means": "required",
        "severity": FindingSeverity.LOW,
        "title": "No entire-agreement / merger clause detected",
        "act_name": "Indian Contract Act, 1872",
        "section": "General Drafting Principle",
        "law_text": (
            "An entire-agreement clause (also called a merger clause) states that the written "
            "contract is the complete and final agreement between the parties and supersedes all "
            "prior negotiations, representations, and understandings. Without it, parties may "
            "introduce extrinsic evidence of prior oral agreements."
        ),
        "jurisdiction": "india",
        "recommendation": "Add an entire-agreement clause to prevent disputes over prior representations.",
        "check_full_text": True,
    },
    # ── Limitation of Liability ───────────────────────────────────────────────────
    {
        "id": "LIABILITY_CAP_missing",
        "pattern": r"\b(limit(ation)? of liabilit\w*|liabilit\w*.{0,30}shall not exceed|cap on liabilit\w*|maximum liabilit\w*)\b",
        "match_means": "required",
        "severity": FindingSeverity.MEDIUM,
        "title": "No limitation of liability clause detected",
        "act_name": "Indian Contract Act, 1872",
        "section": "Section 73 / General Commercial Practice",
        "law_text": (
            "Section 73: When a contract has been broken, the party who suffers by such breach is "
            "entitled to receive, from the party who has broken it, compensation for any loss or damage "
            "caused to him thereby. A cap on liability provides certainty and is standard practice "
            "in commercial contracts."
        ),
        "jurisdiction": "india",
        "recommendation": "Add a limitation of liability clause capping exposure to contract value or a fixed multiple thereof.",
        "check_full_text": True,
    },
]


def _extract_payment_days(text: str) -> int | None:
    """
    Extract the number of payment days explicitly stated in the text.
    Returns None if no explicit day count can be found.
    """
    patterns = [
        r"\bwithin\s+(\d+)\s+(?:calendar\s+)?days?\b",
        r"\bnet[\s-]?(\d+)\b",
        r"\b(\d+)\s+(?:calendar\s+)?days?\s+(?:of|from|after)\s+(?:invoice|receipt)",
        r"\bpayment.{0,30}\b(\d+)\s+days?\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except (ValueError, IndexError):
                pass
    return None


def _should_fire(rule: dict, clause: dict, full_text: str, global_seen: set) -> bool:
    """
    Decide whether a rule should produce a finding for this clause.
    Returns True if the rule fires.
    """
    rule_id = rule["id"]
    text = (clause.get("body_text") or "").strip()
    check_full = rule.get("check_full_text", False)

    if rule["match_means"] == "required":
        # Required rules: fire if pattern is absent from the full text
        if check_full:
            if rule_id in global_seen:
                return False
            found_anywhere = re.search(rule["pattern"], full_text, re.IGNORECASE)
            global_seen.add(rule_id)
            return not found_anywhere
        else:
            # Check only this clause
            return not re.search(rule["pattern"], text, re.IGNORECASE)

    else:  # "violation"
        if not text or len(text) < 30:
            return False

        # Special-case: MSME rule — only fire when explicit days > 45
        if rule_id == "MSME_payment_over_45_days":
            days = _extract_payment_days(text)
            if days is not None:
                return days > 45
            # No explicit day count — don't fire to avoid false positives
            return False

        if rule_id == "PAYMENT_excess_90_days":
            days = _extract_payment_days(text)
            if days is not None:
                return days >= 90
            return False

        return bool(re.search(rule["pattern"], text, re.IGNORECASE))


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
        clauses = context.get("clauses", [])

        self._log_run_start(project_id, tenant_id)

        full_text = " ".join(c.get("body_text", "") for c in clauses)

        # Track which "required" rules that check full text have already been evaluated
        global_seen: set[str] = set()
        # Track rules that already fired per clause (avoid duplicate violations per rule)
        fired_violation_rules: set[str] = set()

        findings = []

        # Per-clause violation checks
        for clause in clauses:
            text = (clause.get("body_text") or "").strip()
            if not text or len(text) < 30:
                continue

            for rule in _RULES:
                if rule["match_means"] != "violation":
                    continue

                rule_id = rule["id"]
                # Avoid the same violation rule firing on multiple clauses
                if rule_id in fired_violation_rules:
                    continue

                if not _should_fire(rule, clause, full_text, global_seen):
                    continue

                fired_violation_rules.add(rule_id)
                match = re.search(rule["pattern"], text, re.IGNORECASE)
                matched_text = match.group(0) if match else None

                findings.append(self._build_finding(
                    flag_type="law_violation",
                    severity=rule["severity"],
                    title=rule["title"],
                    description=(
                        f"Pattern detected: {rule['law_text']}"
                        + (f" Matched text: '{matched_text}'." if matched_text else "")
                    ),
                    recommendation=rule["recommendation"],
                    source_clause_id=str(clause.get("id", "")),
                    confidence=0.82,
                    reasoning_trace=(
                        f"Rule {rule_id}; matched_text='{matched_text}'; "
                        f"clause_heading='{clause.get('heading')}'"
                    ),
                    law_act_name=rule["act_name"],
                    law_section_number=rule["section"],
                    law_retrieved_text=rule["law_text"][:500],
                    law_jurisdiction=rule["jurisdiction"],
                ))

        # Full-text "required" checks (check_full_text=True rules)
        for rule in _RULES:
            if rule["match_means"] != "required":
                continue
            if not rule.get("check_full_text", False):
                continue

            rule_id = rule["id"]
            if rule_id in global_seen:
                continue

            found = re.search(rule["pattern"], full_text, re.IGNORECASE)
            global_seen.add(rule_id)

            if not found:
                # Attach to first clause as anchor, or emit without clause
                anchor_clause = clauses[0] if clauses else None
                findings.append(self._build_finding(
                    flag_type="law_violation",
                    severity=rule["severity"],
                    title=rule["title"],
                    description=f"Clause missing from contract: {rule['law_text']}",
                    recommendation=rule["recommendation"],
                    source_clause_id=str(anchor_clause.get("id", "")) if anchor_clause else None,
                    confidence=0.78,
                    reasoning_trace=f"Rule {rule_id} — pattern '{rule['pattern'][:60]}' not found in full contract text",
                    law_act_name=rule["act_name"],
                    law_section_number=rule["section"],
                    law_retrieved_text=rule["law_text"][:500],
                    law_jurisdiction=rule["jurisdiction"],
                ))

        # Per-clause "required" checks (check_full_text=False) — check each clause independently
        for rule in _RULES:
            if rule["match_means"] != "required":
                continue
            if rule.get("check_full_text", True):
                continue

            rule_id = rule["id"]
            for clause in clauses:
                text = (clause.get("body_text") or "").strip()
                if not text or len(text) < 30:
                    continue
                # Only fire if termination is mentioned but notice is absent
                if not _should_fire(rule, clause, full_text, global_seen):
                    continue
                # Make sure we only fire once
                if rule_id in fired_violation_rules:
                    continue
                fired_violation_rules.add(rule_id)

                findings.append(self._build_finding(
                    flag_type="law_violation",
                    severity=rule["severity"],
                    title=rule["title"],
                    description=f"Clause missing required element: {rule['law_text']}",
                    recommendation=rule["recommendation"],
                    source_clause_id=str(clause.get("id", "")),
                    confidence=0.75,
                    reasoning_trace=f"Rule {rule_id} — pattern not found in clause '{clause.get('heading')}'",
                    law_act_name=rule["act_name"],
                    law_section_number=rule["section"],
                    law_retrieved_text=rule["law_text"][:500],
                    law_jurisdiction=rule["jurisdiction"],
                ))

        self._log_run_complete(project_id, len(findings))

        return {
            "findings": findings,
            "token_usage": {"input_tokens": 0, "output_tokens": 0},
            "model_version": "bundled-indian-law-rules-v2-demo",
            "prompt_version": PROMPT_VERSION,
        }
