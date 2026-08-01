"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { useFindings } from "@/lib/hooks/use-tasks"
import { useProject } from "@/lib/hooks/use-projects"
import { SeverityBadge } from "@/components/findings/severity-badge"
import { FindingDetailSheet } from "@/components/findings/finding-detail-sheet"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { exportApi } from "@/lib/api/export"
import { SEVERITY_CONFIG } from "@/lib/types/api"
import type { ClauseFlag, Severity } from "@/lib/types/api"
import { dedupeFindings, rankByRisk, riskScore } from "@/lib/findings-dedup"
import { Flag, Download, Loader2, ChevronRight, Layers, Sparkles } from "lucide-react"
import { cn, truncate } from "@/lib/utils"
import { toast } from "sonner"
import { useMemo } from "react"

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"]

function effectiveRiskScore(finding: ClauseFlag): number {
  return riskScore(finding)
}

/** Strip the "[tag]" prefix analysts see as noise, for a cleaner headline. */
function cleanTitle(title: string): string {
  return title.replace(/^\s*\[[^\]]+\]\s*/, "").trim()
}

const flagTypeLabels: Record<string, string> = {
  template_deviation: "Template Deviation",
  clause_added: "Clause Added",
  clause_missing: "Clause Missing",
  vendor_redline: "Vendor Redline",
  law_violation: "Law Violation",
  law_at_risk: "Law Risk",
  checklist_violation: "Checklist Fail",
  checklist_fail: "Checklist Fail",
  checklist_not_found: "Not Found",
  missing_clause: "Missing Clause",
  weakened_clause: "Weakened Clause",
  modified: "Modified",
  deleted: "Deleted",
  added: "Added",
}

const reviewStatusClass: Record<string, string> = {
  approved: "bg-success-bg text-success border-success-border",
  rejected: "bg-sev-critical-bg text-sev-critical border-sev-critical-border",
  pending: "bg-sev-medium-bg text-sev-medium border-sev-medium-border",
}

export default function FindingsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { data: project } = useProject(projectId)
  const { data: findings, isLoading } = useFindings(projectId)
  const [selected, setSelected] = useState<ClauseFlag | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [reviewFilter, setReviewFilter] = useState("all")
  const [severityFilter, setSeverityFilter] = useState("all")
  const [exporting, setExporting] = useState(false)

  // Collapse the raw flags into distinct issues (one clause-level issue may be
  // flagged by several agents). This is what turns "196 findings" into a readable memo.
  const issues = useMemo(() => rankByRisk(dedupeFindings(findings ?? [])), [findings])

  const filtered = issues.filter(({ primary }) => {
    if (reviewFilter !== "all" && primary.reviewer_status !== reviewFilter) return false
    if (severityFilter !== "all" && primary.severity !== severityFilter) return false
    return true
  })

  const rawCount = findings?.length ?? 0
  const totalIssues = issues.length
  const critical = issues.filter((i) => i.primary.severity === "critical").length
  const pending = issues.filter((i) => i.primary.reviewer_status === "pending").length

  // The handful a reviewer must read first.
  const topIssues = issues.filter((i) => i.primary.severity === "critical" || i.primary.severity === "high").slice(0, 6)

  // Severity distribution for the meter strip (on deduped issues)
  const sevCounts = SEVERITY_ORDER.map((sev) => ({
    sev,
    label: SEVERITY_CONFIG[sev].label,
    count: issues.filter((i) => i.primary.severity === sev).length,
  }))

  async function handleExport() {
    if (!project) return
    setExporting(true)
    try {
      await exportApi.downloadPdf(projectId, project.name)
      toast.success("PDF exported")
    } catch {
      toast.error("Export failed")
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header + export */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold tracking-[-0.01em] text-foreground">Findings Review</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {rawCount > totalIssues
              ? <>{totalIssues} distinct issues, grouped from {rawCount} raw flags. Highest-risk first.</>
              : <>Review and approve or reject every flagged issue. Highest-risk first.</>}
          </p>
        </div>
        <Button variant="outline" onClick={handleExport} disabled={exporting || !findings?.length}>
          {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
          Export PDF
        </Button>
      </div>

      {/* Top Issues — the handful to read first */}
      {topIssues.length > 0 && (
        <div className="animate-rise rounded-xl border border-sev-critical-border/60 bg-gradient-to-b from-sev-critical-bg/40 to-card p-5 shadow-sm">
          <div className="mb-3 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-sev-critical" />
            <h3 className="text-sm font-semibold text-foreground">Top issues to review first</h3>
            <span className="text-xs text-muted-foreground">— the {topIssues.length} highest-risk changes</span>
          </div>
          <ol className="space-y-1.5">
            {topIssues.map((issue, i) => (
              <li key={issue.primary.id}>
                <button
                  onClick={() => { setSelected(issue.primary); setSheetOpen(true) }}
                  className="group flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-card"
                >
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-secondary text-[0.7rem] font-semibold text-muted-foreground tabular-nums">{i + 1}</span>
                  <SeverityBadge severity={issue.primary.severity} />
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-foreground">{cleanTitle(issue.primary.title)}</span>
                  <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground/40 transition-transform group-hover:translate-x-0.5" />
                </button>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Summary strip: three stats + severity distribution meter */}
      {totalIssues > 0 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
          {/* Stat tiles */}
          <div className="grid grid-cols-3 gap-3 lg:col-span-2">
            <StatTile label="Issues" value={totalIssues} tone="ink" />
            <StatTile label="Critical" value={critical} tone="critical" />
            <StatTile label="Pending" value={pending} tone="medium" />
          </div>

          {/* Distribution meter */}
          <div className="rounded-lg border border-border bg-card p-4 shadow-sm lg:col-span-3">
            <p className="mb-3 text-xs font-medium text-muted-foreground">Severity distribution</p>
            {/* Stacked proportional bar */}
            <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-secondary">
              {sevCounts.filter((s) => s.count > 0).map((s) => (
                <div
                  key={s.sev}
                  className={cn("h-full transition-[width] duration-500 ease-out-quint", SEVERITY_CONFIG[s.sev].dot)}
                  style={{ width: `${(s.count / totalIssues) * 100}%` }}
                  title={`${s.label}: ${s.count}`}
                />
              ))}
            </div>
            {/* Legend */}
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
              {sevCounts.map((s) => (
                <div key={s.sev} className="flex items-center gap-1.5">
                  <span className={cn("h-2 w-2 rounded-full", SEVERITY_CONFIG[s.sev].dot, s.count === 0 && "opacity-30")} />
                  <span className={cn("text-xs", s.count === 0 ? "text-muted-foreground/50" : "text-muted-foreground")}>
                    {s.label} <span className="font-semibold text-foreground tabular-nums">{s.count}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <Tabs value={reviewFilter} onValueChange={setReviewFilter}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="pending">Pending</TabsTrigger>
            <TabsTrigger value="approved">Approved</TabsTrigger>
            <TabsTrigger value="rejected">Rejected</TabsTrigger>
          </TabsList>
        </Tabs>
        <Select value={severityFilter} onValueChange={setSeverityFilter}>
          <SelectTrigger className="h-9 w-36">
            <SelectValue placeholder="All severities" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All severities</SelectItem>
            {SEVERITY_ORDER.map((s) => (
              <SelectItem key={s} value={s} className="capitalize">{SEVERITY_CONFIG[s].label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {filtered.length > 0 && (
          <span className="ml-auto text-xs text-muted-foreground tabular-nums">
            {filtered.length} of {totalIssues} issues shown
          </span>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-lg" />)}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Flag}
          title={totalIssues === 0 ? "No findings yet" : "No issues match the current filters"}
          description={totalIssues === 0 ? "Run an analysis task first to generate findings." : "Try adjusting the filters above."}
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-secondary/60">
                <th className="px-4 py-2.5 text-left text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-muted-foreground">Severity</th>
                <th className="px-4 py-2.5 text-left text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-muted-foreground">Type</th>
                <th className="px-4 py-2.5 text-left text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-muted-foreground">Finding</th>
                <th className="hidden px-4 py-2.5 text-left text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-muted-foreground lg:table-cell">Law Ref</th>
                <th className="hidden px-4 py-2.5 text-left text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-muted-foreground md:table-cell">Risk</th>
                <th className="px-4 py-2.5 text-left text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-muted-foreground">Status</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {filtered.map(({ primary: finding, duplicateCount }) => {
                const score = effectiveRiskScore(finding)
                const barColor = SEVERITY_CONFIG[finding.severity as Severity]?.dot ?? "bg-sev-info"
                return (
                  <tr
                    key={finding.id}
                    className="group cursor-pointer border-b border-border/70 transition-colors last:border-0 hover:bg-secondary/40"
                    onClick={() => { setSelected(finding); setSheetOpen(true) }}
                  >
                    <td className="px-4 py-3"><SeverityBadge severity={finding.severity} /></td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{flagTypeLabels[finding.flag_type] ?? finding.flag_type}</td>
                    <td className="max-w-sm px-4 py-3 font-medium text-foreground">
                      <span className="inline-flex items-center gap-2">
                        {truncate(cleanTitle(finding.title), 64)}
                        {duplicateCount > 1 && (
                          <span
                            title={`Flagged ${duplicateCount} times by different checks — grouped into one issue`}
                            className="inline-flex shrink-0 items-center gap-1 rounded-full bg-secondary px-1.5 py-0.5 text-[0.65rem] font-medium text-muted-foreground"
                          >
                            <Layers className="h-2.5 w-2.5" />{duplicateCount}
                          </span>
                        )}
                      </span>
                    </td>
                    <td className="hidden px-4 py-3 text-xs text-muted-foreground lg:table-cell">
                      {finding.law_act_name ? (
                        <span className="block max-w-[150px] truncate">{finding.law_act_name}</span>
                      ) : <span className="text-muted-foreground/50">—</span>}
                    </td>
                    <td className="hidden px-4 py-3 md:table-cell">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-secondary">
                          <div className={cn("h-full rounded-full", barColor)} style={{ width: `${(score / 10) * 100}%` }} />
                        </div>
                        <span className="text-xs text-muted-foreground tabular-nums">{score}/10</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize",
                        reviewStatusClass[finding.reviewer_status] ?? "bg-secondary text-muted-foreground border-border",
                      )}>
                        {finding.reviewer_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground/40 transition-all duration-150 ease-out-quint group-hover:translate-x-0.5 group-hover:text-muted-foreground" />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <FindingDetailSheet
        finding={selected}
        projectId={projectId}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
      />
    </div>
  )
}

function StatTile({ label, value, tone }: { label: string; value: number; tone: "ink" | "critical" | "medium" }) {
  const toneClass =
    tone === "critical" ? "text-sev-critical"
    : tone === "medium" ? "text-sev-medium"
    : "text-foreground"
  return (
    <div className="rounded-lg border border-border bg-card p-4 text-center shadow-sm">
      <p className={cn("text-2xl font-bold tabular-nums", toneClass)}>{value}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">{label}</p>
    </div>
  )
}
