"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { useProject } from "@/lib/hooks/use-projects"
import { useFindings } from "@/lib/hooks/use-tasks"
import { exportApi } from "@/lib/api/export"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { SeverityBadge } from "@/components/findings/severity-badge"
import type { Severity } from "@/lib/types/api"
import { Download, FileText, Loader2, AlertTriangle } from "lucide-react"
import { toast } from "sonner"

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"]

export default function ExportPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { data: project } = useProject(projectId)
  const { data: findings } = useFindings(projectId)
  const [exporting, setExporting] = useState(false)

  const severityCounts = (findings ?? []).reduce((acc, f) => {
    acc[f.severity] = (acc[f.severity] ?? 0) + 1
    return acc
  }, {} as Record<string, number>)

  const criticalHighCount = (severityCounts["critical"] ?? 0) + (severityCounts["high"] ?? 0)
  const total = findings?.length ?? 0
  const reviewed = (findings ?? []).filter((f) => f.reviewer_status !== "pending").length

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
    <div className="space-y-6 max-w-xl">
      <div>
        <h2 className="text-base font-semibold text-slate-900 mb-1">Export Report</h2>
        <p className="text-sm text-slate-500">
          Generate a branded PDF with all findings, citations, reviewer notes, and risk register.
        </p>
      </div>

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
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="bg-slate-50 rounded-lg p-3">
              <p className="text-xs text-slate-500">Total Findings</p>
              <p className="text-xl font-bold text-slate-900">{total}</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3">
              <p className="text-xs text-slate-500">Reviewed</p>
              <p className="text-xl font-bold text-slate-900">{reviewed}<span className="text-sm font-normal text-slate-400">/{total}</span></p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {SEVERITY_ORDER.map((sev) => {
              const count = severityCounts[sev] ?? 0
              if (!count) return null
              return (
                <div key={sev} className="flex items-center gap-1.5">
                  <SeverityBadge severity={sev} />
                  <span className="text-xs text-slate-600 font-medium">×{count}</span>
                </div>
              )
            })}
          </div>

          {criticalHighCount > 0 && (
            <div className="flex items-start gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{criticalHighCount} critical/high finding{criticalHighCount !== 1 ? "s" : ""} included in risk register</span>
            </div>
          )}

          <div className="text-xs text-slate-500 bg-slate-50 rounded-lg p-3 space-y-1">
            <p className="font-medium text-slate-700">Report contains:</p>
            <ul className="space-y-0.5 ml-3">
              <li>• Cover page with project details</li>
              <li>• Executive summary with severity breakdown</li>
              <li>• Full findings index table</li>
              <li>• Per-finding detail with law citations</li>
              <li>• Risk register (critical + high only)</li>
            </ul>
          </div>

          <Button onClick={handleExport} disabled={exporting || total === 0} className="w-full">
            {exporting ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Generating PDF…</>
            ) : (
              <><Download className="w-4 h-4 mr-2" />Download PDF Report</>
            )}
          </Button>
          {total === 0 && (
            <p className="text-xs text-center text-slate-500">Run analysis tasks first to generate findings</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
