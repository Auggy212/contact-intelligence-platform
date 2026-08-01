import type { ClauseFlag, FlagType } from "@/lib/types/api"

/**
 * Turns an engine finding into plain-English framing a non-lawyer can read:
 *   What changed  → the concrete change, in one line
 *   Why it matters → the risk / consequence
 *   What to do    → the recommended action
 *
 * This is a presentation layer over fields the backend already produces
 * (title, description, recommendation, law citation). It strips analyst jargon
 * like "Text similarity 46%" and "[Clause Type: …]" so the reader sees meaning,
 * not internals.
 */
export interface PlainExplanation {
  whatChanged: string
  whyItMatters: string
  whatToDo: string
}

/** Removes the "[Clause Type: x]" / "[Semantic]" style prefix and similarity noise. */
function stripJargon(text: string): string {
  return (text ?? "")
    .replace(/^\s*\[[^\]]+\]\s*/g, "")
    .replace(/\bText similarity[^.]*\.\s*/gi, "")
    .replace(/\bbest match in [ABC]:\s*\d+%\)?/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim()
}

/** Removes the "[tag]" prefix from a title for a clean headline. */
function cleanTitle(title: string): string {
  return (title ?? "").replace(/^\s*\[[^\]]+\]\s*/, "").trim()
}

const WHY_BY_TYPE: Partial<Record<FlagType, string>> = {
  template_deviation:
    "This clause no longer matches your organisation's approved template. Deviations can shift risk, cost, or obligations away from what your team signed off on.",
  vendor_redline:
    "The vendor changed this clause in their reply. Vendor-favourable edits to liability, payment, termination, or IP terms can expose your company if accepted unreviewed.",
  clause_missing:
    "A clause that exists in your template is missing from this draft. Its protections are simply not in the contract as written.",
  missing_clause:
    "A clause that exists in your template is missing from this draft. Its protections are simply not in the contract as written.",
  clause_added:
    "The vendor added a clause that is not in your template. New obligations can be introduced this way.",
  law_violation:
    "This clause conflicts with Indian law. Unenforceable or void terms can leave your company without the protection it assumes it has.",
  law_at_risk:
    "This clause may conflict with Indian law depending on interpretation. It is worth a legal check before signing.",
  checklist_violation:
    "An extracted value falls outside your company's allowed policy range. This is a hard business rule, not a judgement call.",
  checklist_fail:
    "An extracted value falls outside your company's allowed policy range. This is a hard business rule, not a judgement call.",
  weakened_clause:
    "This clause was weakened relative to your template — the protection it offers is now narrower.",
}

const DEFAULT_WHY =
  "This clause differs from your approved baseline in a way worth a human review before signing."

export function explainFinding(finding: ClauseFlag): PlainExplanation {
  const type = finding.flag_type as FlagType

  const whatChanged = cleanTitle(finding.title) || "A clause differs from the approved baseline."

  // Prefer the (jargon-stripped) description if it adds detail beyond the title,
  // otherwise fall back to the type-based explanation.
  const desc = stripJargon(finding.description)
  const typeWhy = WHY_BY_TYPE[type] ?? DEFAULT_WHY
  const whyItMatters = desc && desc.length > 40 ? desc : typeWhy

  // "What to do" — prefer a concrete suggested fix, then the recommendation,
  // then a law-aware default.
  let whatToDo: string
  if (finding.suggestion?.suggested_text) {
    whatToDo = `Apply the suggested fix below: ${finding.suggestion.suggested_text}`
  } else if (finding.recommendation) {
    whatToDo = stripJargon(finding.recommendation)
  } else if (finding.law_act_name) {
    whatToDo = `Have counsel confirm compliance with ${finding.law_act_name}${finding.law_section_number ? ` (${finding.law_section_number})` : ""} before signing.`
  } else {
    whatToDo = "Confirm this change is intentional and acceptable; otherwise restore the template wording."
  }

  return { whatChanged, whyItMatters, whatToDo }
}
