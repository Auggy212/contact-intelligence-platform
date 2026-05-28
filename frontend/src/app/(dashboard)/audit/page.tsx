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
import { useStaggerReveal } from "@/hooks/use-scroll-reveal"

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

  const revealRef = useStaggerReveal<HTMLTableSectionElement>(30)

  return (
    <div>
      <div className="animate-fade-up">
        <PageHeader
          title="Audit Log"
          description="Complete compliance trail of all actions in this organisation"
        />
      </div>

      <div className="flex items-center gap-3 mb-6 animate-fade-in delay-75">
        <Select value={actionFilter} onValueChange={setActionFilter}>
          <SelectTrigger className="w-52 h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-zinc-300 focus:ring-2 focus:ring-orange-500/10 transition-all duration-200">
            <SelectValue placeholder="All actions" />
          </SelectTrigger>
          <SelectContent className="border-white/[0.08] bg-[#1C1E26]">
            <SelectItem value="all" className="text-zinc-300">All actions</SelectItem>
            {ACTION_OPTIONS.map((a) => (
              <SelectItem key={a} value={a} className="text-zinc-300">{ACTION_LABELS[a] ?? a}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="space-y-2">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-12 rounded-lg" />)}</div>
      ) : !logs?.length ? (
        <div className="animate-fade-in delay-100">
          <EmptyState icon={Shield} title="No audit records" description="Audit records appear as actions are taken in the platform" />
        </div>
      ) : (
        <>
          <div className="rounded-2xl border border-white/[0.07] bg-[#111111] overflow-hidden animate-scale-in delay-100 hover:border-white/[0.1] transition-all duration-300">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                  <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-widest text-zinc-600">Timestamp</th>
                  <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-widest text-zinc-600">Action</th>
                  <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-widest text-zinc-600 hidden md:table-cell">Resource</th>
                  <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-widest text-zinc-600 hidden lg:table-cell">IP</th>
                </tr>
              </thead>
              <tbody ref={revealRef}>
                {logs.map((log) => (
                  <tr key={log.id} className="reveal border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] transition-all duration-200">
                    <td className="px-4 py-3 text-xs text-zinc-500 whitespace-nowrap">{formatDateTime(log.created_at)}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-semibold text-white">{ACTION_LABELS[log.action] ?? log.action}</span>
                      <code className="ml-2 text-xs text-zinc-600 bg-white/[0.03] px-1 py-0.5 rounded font-mono">{log.action}</code>
                    </td>
                    <td className="px-4 py-3 text-xs text-zinc-500 hidden md:table-cell">
                      {log.resource_type && (
                        <span className="bg-orange-500/12 text-orange-400 border border-orange-500/20 px-1.5 py-0.5 rounded text-xs">{log.resource_type}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-zinc-600 hidden lg:table-cell font-mono">
                      {log.ip_address ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between mt-4 animate-fade-in delay-150">
            <p className="text-xs text-zinc-500 font-medium">Showing {page * PAGE_SIZE + 1}–{page * PAGE_SIZE + (logs?.length ?? 0)}</p>
            <div className="flex gap-2">
              <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.03] text-zinc-300 transition-all hover:border-orange-500/25 hover:text-orange-400 hover:scale-105 active:scale-95 disabled:opacity-30 disabled:scale-100 disabled:pointer-events-none duration-200">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button disabled={(logs?.length ?? 0) < PAGE_SIZE} onClick={() => setPage((p) => p + 1)}
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.03] text-zinc-300 transition-all hover:border-orange-500/25 hover:text-orange-400 hover:scale-105 active:scale-95 disabled:opacity-30 disabled:scale-100 disabled:pointer-events-none duration-200">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
