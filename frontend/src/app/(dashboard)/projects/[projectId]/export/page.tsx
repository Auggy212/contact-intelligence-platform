"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { useProject } from "@/lib/hooks/use-projects"
import { useFindings } from "@/lib/hooks/use-tasks"
import { dedupeFindings } from "@/lib/findings-dedup"
import { exportApi } from "@/lib/api/export"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { SeverityBadge } from "@/components/findings/severity-badge"
import type { Severity, TaskType } from "@/lib/types/api"
import { Download, FileText, Loader2, AlertTriangle, Filter } from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"]

const TASK_SECTIONS: { type: TaskType; label: string; description: string }[] = [
  { type: "template_comparison", label: "Template Comparison", description: "Clauses missing or altered vs your template" },
  { type: "vendor_diff", label: "Vendor Diff Analysis", description: "Vendor modifications and redlines" },
  { type: "law_validation", label: "Indian Law Validation", description: "Compliance findings from Indian statutes" },
  { type: "checklist_validation", label: "Checklist Validation", description: "Business rule violations" },
]

const SEVERITY_LABELS: Record<Severity, string> = {
  critical: "Critical", high: "High", medium: "Medium", low: "Low", info: "Info",
}

export default function ExportPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { data: project } = useProject(projectId)
  const { data: findings } = useFindings(projectId)
  const [exporting, setExporting] = useState(false)

  const [includedSeverities, setIncludedSeverities] = useState<Set<Severity>>(
    new Set(["critical", "high", "medium", "low", "info"])
  )
  const [includedTasks, setIncludedTasks] = useState<Set<TaskType>>(
    new Set(["template_comparison", "vendor_diff", "law_validation", "checklist_validation"])
  )

  // Count DISTINCT issues (deduped) so Export agrees with Findings / Overview.
  const issues = findings ? dedupeFindings(findings).map((i) => i.primary) : []
  const severityCounts = issues.reduce((acc, f) => {
    acc[f.severity] = (acc[f.severity] ?? 0) + 1
    return acc
  }, {} as Record<string, number>)

  const filteredFindings = issues.filter(
    (f) => includedSeverities.has(f.severity as Severity)
  )

  const total = issues.length
  const filteredTotal = filteredFindings.length
  const reviewed = filteredFindings.filter((f) => f.reviewer_status !== "pending").length
  const criticalHighCount = filteredFindings.filter(
    (f) => f.severity === "critical" || f.severity === "high"
  ).length

  function toggleSeverity(s: Severity) {
    setIncludedSeverities((prev) => {
      const next = new Set(prev)
      if (next.has(s)) { next.delete(s) } else { next.add(s) }
      return next
    })
  }

  function toggleTask(t: TaskType) {
    setIncludedTasks((prev) => {
      const next = new Set(prev)
      if (next.has(t)) { next.delete(t) } else { next.add(t) }
      return next
    })
  }

  async function handleExport() {
    if (!project) return
    setExporting(true)
    try {
      await exportApi.downloadPdf(projectId, project.name)
      toast.success("PDF downloaded")
    } catch {
      toast.error("Export failed — please try again")
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-base font-semibold text-slate-900 mb-1">Export Report</h2>
        <p className="text-sm text-slate-500">
          Configure what to include in the PDF, then download the full report.
        </p>
      </div>

      {/* Filter — Severity */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <CardTitle className="text-sm">Include Severity Levels</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex flex-wrap gap-3">
            {SEVERITY_ORDER.map((sev) => {
              const count = severityCounts[sev] ?? 0
              const checked = includedSeverities.has(sev)
              return (
                <label
                  key={sev}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer transition-colors select-none",
                    checked ? "bg-slate-50 border-slate-300" : "border-slate-200 opacity-50"
                  )}
                >
                  <Checkbox
                    checked={checked}
                    onCheckedChange={() => toggleSeverity(sev)}
                    disabled={count === 0}
                  />
                  <SeverityBadge severity={sev} />
                  <span className="text-xs text-slate-500 font-medium">{count}</span>
                </label>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Filter — Task sections */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <CardTitle className="text-sm">Include Analysis Sections</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="pt-0 space-y-2">
          {TASK_SECTIONS.map((section) => (
            <label
              key={section.type}
              className={cn(
                "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors select-none",
                includedTasks.has(section.type) ? "bg-slate-50 border-slate-300" : "border-slate-200 opacity-50"
              )}
            >
              <Checkbox
                checked={includedTasks.has(section.type)}
                onCheckedChange={() => toggleTask(section.type)}
                className="mt-0.5"
              />
              <div>
                <p className="text-sm font-medium text-slate-800">{section.label}</p>
                <p className="text-xs text-slate-500 mt-0.5">{section.description}</p>
              </div>
            </label>
          ))}
        </CardContent>
      </Card>

      {/* Report preview */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <CardTitle className="text-sm">{project?.name ?? "Contract Review Report"}</CardTitle>
              <p className="text-xs text-slate-500 mt-0.5">Multi-section PDF with findings + risk register</p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0 space-y-4">
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div className="bg-slate-50 rounded-lg p-3">
              <p className="text-xs text-slate-500">Included Findings</p>
              <p className="text-xl font-bold text-slate-900">
                {filteredTotal}
                {filteredTotal !== total && (
                  <span className="text-sm font-normal text-slate-400">/{total}</span>
                )}
              </p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3">
              <p className="text-xs text-slate-500">Reviewed</p>
              <p className="text-xl font-bold text-slate-900">
                {reviewed}<span className="text-sm font-normal text-slate-400">/{filteredTotal}</span>
              </p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3">
              <p className="text-xs text-slate-500">In Risk Register</p>
              <p className="text-xl font-bold text-red-600">{criticalHighCount}</p>
            </div>
          </div>

          {criticalHighCount > 0 && (
            <div className="flex items-start gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{criticalHighCount} critical/high finding{criticalHighCount !== 1 ? "s" : ""} will appear in the risk register section</span>
            </div>
          )}

          <div className="text-xs text-slate-500 bg-slate-50 rounded-lg p-3 space-y-1">
            <p className="font-medium text-slate-700">Report sections:</p>
            <ul className="space-y-0.5 ml-3">
              <li>• Cover page with project details and document manifest</li>
              <li>• Executive summary with KPI dashboard + severity chart</li>
              <li>• Full findings index table</li>
              {Array.from(includedTasks).map((t) => {
                const s = TASK_SECTIONS.find((x) => x.type === t)
                return s ? <li key={t}>• {s.label} findings with law citations</li> : null
              })}
              {criticalHighCount > 0 && <li>• Risk register (critical + high only)</li>}
            </ul>
          </div>

          <Button
            onClick={handleExport}
            disabled={exporting || filteredTotal === 0 || includedTasks.size === 0}
            className="w-full"
          >
            {exporting ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Generating PDF…</>
            ) : (
              <><Download className="w-4 h-4 mr-2" />Download PDF Report</>
            )}
          </Button>
          {total === 0 && (
            <p className="text-xs text-center text-slate-500">Run analysis tasks first to generate findings</p>
          )}
          {total > 0 && filteredTotal === 0 && (
            <p className="text-xs text-center text-slate-500">No findings match the selected filters</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
