"use client"

import { useParams, useRouter } from "next/navigation"
import { useModifications, useFindings } from "@/lib/hooks/use-tasks"
import { Skeleton } from "@/components/ui/skeleton"
import { SeverityBadge } from "@/components/findings/severity-badge"
import { EmptyState } from "@/components/shared/empty-state"
import { cn } from "@/lib/utils"
import { PRIORITY_CONFIG, type SuggestionPriority, type ModificationItem } from "@/lib/types/api"
import { ArrowRight, CheckCircle2, ClipboardList, RefreshCw } from "lucide-react"

const PRIORITY_ORDER: SuggestionPriority[] = ["must_fix", "should_fix", "optional"]

const BASIS_LABEL: Record<string, string> = {
  template: "vs. Template",
  vendor_draft: "vs. Agreed Draft",
  statute: "Legal Requirement",
  checklist_rule: "Checklist Rule",
  concept: "Concept Analysis",
}

function ModificationCard({ item, index }: { item: ModificationItem; index: number }) {
  const s = item.suggestion
  return (
    <div
      className="animate-rise rounded-lg border border-border bg-card p-4 shadow-sm transition-all duration-200 ease-out-quint hover:border-border hover:shadow-md"
      style={{ animationDelay: `${Math.min(index * 40, 320)}ms` }}
    >
      <div className="mb-3 flex items-center gap-2">
        <SeverityBadge severity={item.severity} />
        {item.clause_type && (
          <span className="text-xs capitalize text-muted-foreground">{item.clause_type.replace(/_/g, " ")}</span>
        )}
        <span className="ml-auto rounded-full bg-secondary px-2 py-0.5 text-[0.7rem] font-medium text-muted-foreground">
          {BASIS_LABEL[s.basis] ?? s.basis}
        </span>
      </div>

      <p className="mb-3 text-sm font-medium leading-snug text-foreground">{item.title}</p>

      {/* Current → Fix */}
      <div className="space-y-2 rounded-md border border-border/70 bg-secondary/40 p-3 text-sm">
        <div className="flex items-start gap-2.5">
          <span className="w-14 shrink-0 pt-0.5 text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-muted-foreground">Current</span>
          <span className="text-muted-foreground line-through decoration-sev-critical/50">{s.original_text}</span>
        </div>
        <div className="flex items-start gap-2.5">
          <span className="flex w-14 shrink-0 items-center gap-1 pt-0.5 text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-success">
            <ArrowRight className="h-3 w-3" /> Fix
          </span>
          <span className="font-medium text-foreground">{s.suggested_text}</span>
        </div>
      </div>

      <p className="mt-3 text-pretty text-xs leading-relaxed text-muted-foreground">
        <span className="font-semibold text-foreground/80">Why: </span>{s.reason}
      </p>
    </div>
  )
}

export default function ModificationsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const router = useRouter()
  const { data, isLoading } = useModifications(projectId)
  const { data: findings } = useFindings(projectId)

  if (isLoading) {
    return (
      <div className="max-w-3xl space-y-4">
        <Skeleton className="h-24 w-full" />
        <div className="grid grid-cols-3 gap-3">
          <Skeleton className="h-20" /><Skeleton className="h-20" /><Skeleton className="h-20" />
        </div>
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (!data || data.total === 0) {
    const hasFindings = (findings?.length ?? 0) > 0
    // Findings exist but no suggestions → this project was analyzed before the
    // Fixes feature existed. Re-running analysis will generate suggestions.
    if (hasFindings) {
      return (
        <EmptyState
          icon={RefreshCw}
          title="Re-run analysis to generate fixes"
          description={`This project has ${findings!.length} findings, but they were analyzed before suggested fixes were added. Re-run the analysis and every fixable finding will get a plain-English suggestion here.`}
          action={{ label: "Go to Analysis", onClick: () => router.push(`/projects/${projectId}/analysis`) }}
        />
      )
    }
    return (
      <EmptyState
        icon={ClipboardList}
        title="No suggested fixes yet"
        description="Run an analysis first — every finding with a fixable issue will produce a suggestion here."
        action={{ label: "Go to Analysis", onClick: () => router.push(`/projects/${projectId}/analysis`) }}
      />
    )
  }

  const grouped = PRIORITY_ORDER.map((prio) => ({
    priority: prio,
    items: data.modifications.filter((m) => m.priority === prio),
  })).filter((g) => g.items.length > 0)

  let cardIndex = 0

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold tracking-[-0.01em] text-foreground">Suggested Fixes</h2>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Deterministic, rule-based corrections derived from your template, the checklist rules,
          and applicable Indian law. Review each and apply what you agree with.
        </p>
      </div>

      {/* Priority counts */}
      <div className="grid grid-cols-3 gap-3">
        {PRIORITY_ORDER.map((prio) => {
          const cfg = PRIORITY_CONFIG[prio]
          return (
            <div key={prio} className={cn("rounded-lg border p-4 text-center shadow-sm", cfg.bg, cfg.border)}>
              <p className={cn("text-2xl font-bold tabular-nums", cfg.color)}>{data.counts[prio] ?? 0}</p>
              <p className={cn("mt-0.5 text-xs font-medium", cfg.color)}>{cfg.label}</p>
            </div>
          )
        })}
      </div>

      {/* Grouped modifications */}
      {grouped.map((group) => {
        const cfg = PRIORITY_CONFIG[group.priority]
        return (
          <div key={group.priority} className="space-y-3">
            <div className="flex items-center gap-2">
              <span className={cn("h-2 w-2 rounded-full", cfg.dot)} />
              <h3 className={cn("text-xs font-semibold uppercase tracking-[0.05em]", cfg.color)}>
                {cfg.label}
              </h3>
              <span className="text-xs text-muted-foreground tabular-nums">({group.items.length})</span>
            </div>
            <div className="space-y-3">
              {group.items.map((item) => (
                <ModificationCard key={item.id} item={item} index={cardIndex++} />
              ))}
            </div>
          </div>
        )
      })}

      <div className="flex items-center gap-2 border-t border-border pt-4 text-xs text-muted-foreground">
        <CheckCircle2 className="h-3.5 w-3.5 text-success" />
        Suggestions are generated deterministically — no AI guesswork, fully auditable.
      </div>
    </div>
  )
}
