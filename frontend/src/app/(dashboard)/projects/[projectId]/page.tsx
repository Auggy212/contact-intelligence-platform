"use client"

import { useParams } from "next/navigation"
import Link from "next/link"
import { useProject } from "@/lib/hooks/use-projects"
import { useDocuments } from "@/lib/hooks/use-documents"
import { useFindings } from "@/lib/hooks/use-tasks"
import { dedupeFindings } from "@/lib/findings-dedup"
import { useProjectAudit } from "@/lib/hooks/use-audit"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ProjectStatusBadge } from "@/components/projects/project-status-badge"
import { Skeleton } from "@/components/ui/skeleton"
import { formatDate, formatBytes, formatRelative } from "@/lib/utils"
import { FILE_ROLE_LABELS, SEVERITY_CONFIG } from "@/lib/types/api"
import {
  Upload, Flag, FileText, AlertTriangle, Shield,
  UploadCloud, BarChart2, CheckCircle2, XCircle, RefreshCw, Gavel,
} from "lucide-react"

const ACTION_CONFIG: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  "document.upload":    { label: "Document uploaded",      icon: UploadCloud,   color: "text-blue-500" },
  "document.delete":    { label: "Document removed",       icon: XCircle,       color: "text-red-500" },
  "task.create":        { label: "Analysis started",       icon: BarChart2,     color: "text-violet-500" },
  "finding.approved":   { label: "Finding approved",       icon: CheckCircle2,  color: "text-green-500" },
  "finding.rejected":   { label: "Finding rejected",       icon: XCircle,       color: "text-red-500" },
  "project.update":     { label: "Project edited",         icon: RefreshCw,     color: "text-amber-500" },
  "project.delete":     { label: "Project deleted",        icon: XCircle,       color: "text-red-500" },
}

export default function ProjectOverviewPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { data: project, isLoading: loadingProject } = useProject(projectId)
  const { data: documents } = useDocuments(projectId)
  const { data: findings } = useFindings(projectId)
  const { data: auditEvents } = useProjectAudit(projectId, 6)

  // Count DISTINCT issues (deduped), so Overview agrees with the Findings tab.
  const issues = findings ? dedupeFindings(findings).map((i) => i.primary) : []
  const severityCounts = issues.reduce((acc, f) => {
    acc[f.severity] = (acc[f.severity] ?? 0) + 1
    return acc
  }, {} as Record<string, number>)

  if (loadingProject) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 rounded-lg" />
        <div className="grid grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-20 rounded-lg" />)}
        </div>
      </div>
    )
  }

  if (!project) return null

  const criticalCount = severityCounts["critical"] ?? 0
  const totalFindings = issues.length
  const pendingReview = issues.filter((f) => f.reviewer_status === "pending").length

  return (
    <div className="space-y-6">
      {/* Status bar */}
      <Card>
        <CardContent className="pt-5 pb-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <ProjectStatusBadge status={project.status} />
                {criticalCount > 0 && (
                  <span className="inline-flex items-center gap-1 text-xs text-red-600 bg-red-50 border border-red-200 rounded-full px-2 py-0.5">
                    <AlertTriangle className="w-3 h-3" /> {criticalCount} critical
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500">Created {formatDate(project.created_at)}</p>
              {project.description && <p className="text-sm text-slate-600 mt-1">{project.description}</p>}
            </div>
            <div className="flex gap-2">
              <Button asChild variant="outline" size="sm">
                <Link href={`/projects/${project.id}/upload`}><Upload className="w-3.5 h-3.5 mr-1.5" />Upload</Link>
              </Button>
              <Button asChild size="sm">
                <Link href={`/projects/${project.id}/findings`}><Flag className="w-3.5 h-3.5 mr-1.5" />Review Findings</Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Documents</p>
            <p className="text-3xl font-bold text-slate-900 mt-1">{documents?.length ?? 0}<span className="text-base font-normal text-slate-400">/3</span></p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Issues</p>
            <p className="text-3xl font-bold text-slate-900 mt-1">{totalFindings}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Pending Review</p>
            <p className="text-3xl font-bold text-slate-900 mt-1">{pendingReview}</p>
          </CardContent>
        </Card>
      </div>

      {/* Documents */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Documents</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          {!documents || documents.length === 0 ? (
            <div className="text-sm text-slate-500 py-4 text-center">
              No documents uploaded yet.{" "}
              <Link href={`/projects/${project.id}/upload`} className="text-blue-600 hover:underline">Upload now →</Link>
            </div>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => {
                const roleInfo = FILE_ROLE_LABELS[doc.file_role]
                return (
                  <div key={doc.id} className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 border">
                    <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">{doc.original_filename}</p>
                      <p className="text-xs text-slate-500">{roleInfo.label} • {formatBytes(doc.file_size_bytes)}</p>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full border capitalize ${
                      doc.parse_status === "completed" ? "bg-green-50 text-green-700 border-green-200" :
                      doc.parse_status === "failed" ? "bg-red-50 text-red-700 border-red-200" :
                      "bg-blue-50 text-blue-700 border-blue-200"
                    }`}>{doc.parse_status}</span>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Severity breakdown */}
      {totalFindings > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Finding Severity Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex gap-3 flex-wrap">
              {(["critical", "high", "medium", "low", "info"] as const).map((sev) => {
                const count = severityCounts[sev] ?? 0
                if (!count) return null
                const cfg = SEVERITY_CONFIG[sev]
                return (
                  <div key={sev} className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${cfg.bg} ${cfg.border}`}>
                    <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
                    <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}: {count}</span>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Project Activity */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-slate-400" />
              <CardTitle className="text-base">Recent Activity</CardTitle>
            </div>
            <Link href="/audit" className="text-xs text-blue-600 hover:underline">
              Full audit log →
            </Link>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {!auditEvents || auditEvents.length === 0 ? (
            <p className="text-sm text-slate-400 py-3 text-center">No activity recorded yet for this project.</p>
          ) : (
            <div className="space-y-0">
              {auditEvents.map((event, i) => {
                const cfg = ACTION_CONFIG[event.action]
                const Icon = cfg?.icon ?? Gavel
                const label = cfg?.label ?? event.action.replace(/\./g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
                const color = cfg?.color ?? "text-slate-400"
                const meta = event.extra_data as Record<string, string> | null
                const detail =
                  meta?.filename ?? meta?.task_type ?? meta?.flag_type ?? meta?.project_name ?? null

                return (
                  <div
                    key={event.id}
                    className={`flex items-start gap-3 py-3 ${i < auditEvents.length - 1 ? "border-b border-slate-100" : ""}`}
                  >
                    <div className={`mt-0.5 ${color}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-800 font-medium">{label}</p>
                      {detail && (
                        <p className="text-xs text-slate-500 truncate mt-0.5">{detail}</p>
                      )}
                    </div>
                    <span className="text-xs text-slate-400 shrink-0">{formatRelative(event.created_at)}</span>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
