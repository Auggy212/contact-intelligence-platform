"use client"

import { useState } from "react"
import { useAuditLog } from "@/lib/hooks/use-audit"
import { PageHeader } from "@/components/shared/page-header"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Shield, ChevronLeft, ChevronRight } from "lucide-react"
import { formatDateTime } from "@/lib/utils"

const ACTION_LABELS: Record<string, string> = {
  "document.upload": "Document Uploaded",
  "task.create": "Task Created",
  "finding.approved": "Finding Approved",
  "finding.rejected": "Finding Rejected",
  "checklist_rule.create": "Rule Created",
  "checklist_rule.update": "Rule Updated",
  "checklist_rule.delete": "Rule Deleted",
  "clause_library.save": "Clause Saved",
  "user.invite": "Member Invited",
  "user.remove": "Member Removed",
  "project.create": "Project Created",
  "project.delete": "Project Deleted",
}

const PAGE_SIZE = 50

const ACTION_OPTIONS = [
  "document.upload", "task.create", "finding.approved", "finding.rejected",
  "checklist_rule.create", "checklist_rule.update", "checklist_rule.delete",
  "clause_library.save", "user.invite", "user.remove", "project.create",
]

export default function AuditPage() {
  const [page, setPage] = useState(0)
  const [actionFilter, setActionFilter] = useState<string>("all")
  const { data: logs, isLoading } = useAuditLog(page * PAGE_SIZE, PAGE_SIZE, actionFilter === "all" ? undefined : actionFilter)

  return (
    <div>
      <PageHeader
        title="Audit Log"
        description="Complete compliance trail of all actions in this organisation"
      />

      <div className="flex items-center gap-3 mb-6">
        <Select value={actionFilter} onValueChange={setActionFilter}>
          <SelectTrigger className="w-52">
            <SelectValue placeholder="All actions" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All actions</SelectItem>
            {ACTION_OPTIONS.map((a) => (
              <SelectItem key={a} value={a}>{ACTION_LABELS[a] ?? a}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="space-y-2">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-12 rounded-lg" />)}</div>
      ) : !logs?.length ? (
        <EmptyState icon={Shield} title="No audit records" description="Audit records appear as actions are taken in the platform" />
      ) : (
        <>
          <div className="bg-white rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-slate-50">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Timestamp</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Action</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Resource</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">IP</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b last:border-0 hover:bg-slate-50">
                    <td className="px-4 py-3 text-xs text-slate-500 whitespace-nowrap">{formatDateTime(log.created_at)}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium text-slate-800">{ACTION_LABELS[log.action] ?? log.action}</span>
                      <code className="ml-2 text-xs text-slate-400">{log.action}</code>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500 hidden md:table-cell">
                      {log.resource_type && (
                        <span className="bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">{log.resource_type}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400 hidden lg:table-cell font-mono">
                      {log.ip_address ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between mt-4">
            <p className="text-xs text-slate-500">Showing {page * PAGE_SIZE + 1}–{page * PAGE_SIZE + (logs?.length ?? 0)}</p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="sm" disabled={(logs?.length ?? 0) < PAGE_SIZE} onClick={() => setPage((p) => p + 1)}>
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
