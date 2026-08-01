import type { ClauseFlag, Severity } from "@/lib/types/api"

const SEVERITY_RANK: Record<Severity, number> = {
  critical: 5, high: 4, medium: 3, low: 2, info: 1,
}

const SEVERITY_RISK_FALLBACK: Record<Severity, number> = {
  critical: 9, high: 7, medium: 5, low: 3, info: 1,
}

export function riskScore(f: ClauseFlag): number {
  return f.risk_score ?? SEVERITY_RISK_FALLBACK[f.severity as Severity] ?? 5
}

export interface DedupedFinding {
  /** The representative finding (highest severity / risk of the group). */
  primary: ClauseFlag
  /** All findings collapsed into this one issue (including the primary). */
  members: ClauseFlag[]
  /** How many raw findings this issue represents. */
  duplicateCount: number
}

/**
 * Normalises a finding title so that exact-duplicate flags collapse together.
 * Strips the leading "[tag]" marker and whitespace noise, lowercases.
 */
function titleKey(f: ClauseFlag): string {
  const raw = (f.title ?? "").replace(/^\s*\[[^\]]+\]\s*/, "")
  return raw.toLowerCase().replace(/\s+/g, " ").trim()
}

function pickPrimary(members: ClauseFlag[]): ClauseFlag {
  return [...members].sort((a, b) => {
    const sev = SEVERITY_RANK[b.severity as Severity] - SEVERITY_RANK[a.severity as Severity]
    if (sev !== 0) return sev
    return riskScore(b) - riskScore(a)
  })[0]
}

/**
 * Collapses duplicate / overlapping findings into distinct ISSUES.
 *
 * Real analysis output has two kinds of redundancy:
 *  1. Multi-angle on one clause — the same clause gets a semantic flag, a
 *     template-text flag, a value-change flag and a vendor-redline flag, all
 *     describing the SAME underlying change (e.g. "IP ownership reversed").
 *     These share a clause_id and collapse into one issue with sub-points.
 *  2. Same change seen twice — an identical value change ("24 → 48 months")
 *     extracted from two different clause positions. These share a normalised
 *     title and collapse into one issue.
 *
 * The reviewer then reads ~distinct issues instead of a wall of raw flags.
 */
export function dedupeFindings(findings: ClauseFlag[]): DedupedFinding[] {
  // Pass 1: group everything sharing a clause_id (multi-angle on one clause).
  const byClause = new Map<string, ClauseFlag[]>()
  for (const f of findings) {
    // Findings without a clause_id can't be clause-grouped; give each its own bucket.
    const key = f.clause_id ? `clause:${f.clause_id}` : `solo:${f.id}`
    const bucket = byClause.get(key)
    if (bucket) bucket.push(f)
    else byClause.set(key, [f])
  }

  // Pass 2: across clause-groups, fold together any that share a normalised
  // representative title (same change extracted from two clauses).
  const byTitle = new Map<string, ClauseFlag[]>()
  for (const members of Array.from(byClause.values())) {
    const primary = pickPrimary(members)
    const tkey = titleKey(primary)
    const bucket = byTitle.get(tkey)
    if (bucket) bucket.push(...members)
    else byTitle.set(tkey, [...members])
  }

  const deduped: DedupedFinding[] = []
  for (const members of Array.from(byTitle.values())) {
    deduped.push({
      primary: pickPrimary(members),
      members,
      duplicateCount: members.length,
    })
  }

  return deduped
}

/** Ranks deduped findings most-severe / highest-risk first. */
export function rankByRisk(items: DedupedFinding[]): DedupedFinding[] {
  return [...items].sort((a, b) => {
    const sev = SEVERITY_RANK[b.primary.severity as Severity] - SEVERITY_RANK[a.primary.severity as Severity]
    if (sev !== 0) return sev
    return riskScore(b.primary) - riskScore(a.primary)
  })
}
