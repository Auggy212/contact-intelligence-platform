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
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts"
import { Flag, Download, Loader2 } from "lucide-react"
import { cn, truncate } from "@/lib/utils"
import { toast } from "sonner"

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"]

const flagTypeLabels: Record<string, string> = {
  missing_clause: "Missing Clause",
  weakened_clause: "Weakened Clause",
  modified: "Modified",
  deleted: "Deleted",
  added: "Added",
  law_violation: "Law Violation",
  law_at_risk: "Law Risk",
  checklist_fail: "Checklist Fail",
  checklist_not_found: "Not Found",
}

const severityChartColors: Record<Severity, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#3b82f6",
  info: "#94a3b8",
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

  const filtered = (findings ?? []).filter((f) => {
    if (reviewFilter !== "all" && f.reviewer_status !== reviewFilter) return false
    if (severityFilter !== "all" && f.severity !== severityFilter) return false
    return true
  })

  const severityData = SEVERITY_ORDER.map((sev) => ({
    name: SEVERITY_CONFIG[sev].label,
    count: (findings ?? []).filter((f) => f.severity === sev).length,
    sev,
  })).filter((d) => d.count > 0)

  const totalFindings = findings?.length ?? 0
  const critical = (findings ?? []).filter((f) => f.severity === "critical").length
  const pending = (findings ?? []).filter((f) => f.reviewer_status === "pending").length

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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Findings Review</h2>
          <p className="text-sm text-slate-500 mt-0.5">Review and approve/reject AI-flagged issues</p>
        </div>
        <Button variant="outline" onClick={handleExport} disabled={exporting || !findings?.length}>
          {exporting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
          Export PDF
        </Button>
      </div>

      {/* Summary stats + chart */}
      {totalFindings > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-1 grid grid-cols-3 gap-3">
            {[
              { label: "Total", value: totalFindings, color: "text-slate-900" },
              { label: "Critical", value: critical, color: "text-red-600" },
              { label: "Pending", value: pending, color: "text-amber-600" },
            ].map((s) => (
              <div key={s.label} className="bg-white rounded-lg border p-4 text-center">
                <p className={cn("text-2xl font-bold", s.color)}>{s.value}</p>
                <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
          <div className="lg:col-span-2 bg-white rounded-lg border p-4">
            <p className="text-xs font-medium text-slate-500 mb-3">Findings by Severity</p>
            <ResponsiveContainer width="100%" height={80}>
              <BarChart data={severityData} barSize={28}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip
                  formatter={(v: number) => [v, "Findings"]}
                  contentStyle={{ fontSize: 12, borderRadius: 6 }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {severityData.map((entry) => (
                    <Cell key={entry.sev} fill={severityChartColors[entry.sev]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <Tabs value={reviewFilter} onValueChange={setReviewFilter}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="pending">Pending</TabsTrigger>
            <TabsTrigger value="approved">Approved</TabsTrigger>
            <TabsTrigger value="rejected">Rejected</TabsTrigger>
          </TabsList>
        </Tabs>
        <Select value={severityFilter} onValueChange={setSeverityFilter}>
          <SelectTrigger className="w-36 h-9">
            <SelectValue placeholder="All severities" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All severities</SelectItem>
            {SEVERITY_ORDER.map((s) => (
              <SelectItem key={s} value={s} className="capitalize">{SEVERITY_CONFIG[s].label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-lg" />)}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Flag}
          title={totalFindings === 0 ? "No findings yet" : "No findings match the current filters"}
          description={totalFindings === 0 ? "Run an analysis task first to generate findings" : "Try adjusting the filters above"}
        />
      ) : (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Severity</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Type</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Title</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Law Ref</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Risk</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((finding) => (
                <tr
                  key={finding.id}
                  className="border-b last:border-0 hover:bg-slate-50 transition-colors cursor-pointer"
                  onClick={() => { setSelected(finding); setSheetOpen(true) }}
                >
                  <td className="px-4 py-3"><SeverityBadge severity={finding.severity} /></td>
                  <td className="px-4 py-3 text-xs text-slate-500">{flagTypeLabels[finding.flag_type] ?? finding.flag_type}</td>
                  <td className="px-4 py-3 font-medium text-slate-800 max-w-xs">{truncate(finding.title, 60)}</td>
                  <td className="px-4 py-3 text-xs text-slate-500 hidden lg:table-cell">
                    {finding.law_act_name ? (
                      <span className="truncate max-w-[140px] block">{finding.law_act_name}</span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    {finding.risk_score != null ? (
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-slate-200">
                          <div
                            className={cn("h-full rounded-full", finding.risk_score >= 7 ? "bg-red-500" : finding.risk_score >= 4 ? "bg-orange-400" : "bg-blue-400")}
                            style={{ width: `${(finding.risk_score / 10) * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-500">{finding.risk_score}/10</span>
                      </div>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn("text-xs px-2 py-0.5 rounded-full border capitalize font-medium",
                      finding.reviewer_status === "approved" && "bg-green-50 text-green-700 border-green-200",
                      finding.reviewer_status === "rejected" && "bg-red-50 text-red-700 border-red-200",
                      finding.reviewer_status === "pending" && "bg-amber-50 text-amber-700 border-amber-200",
                    )}>
                      {finding.reviewer_status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Button size="sm" variant="ghost" className="text-xs h-7">Review</Button>
                  </td>
                </tr>
              ))}
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
