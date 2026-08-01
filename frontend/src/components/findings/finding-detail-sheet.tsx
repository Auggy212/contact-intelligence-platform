"use client"

import { useState } from "react"
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { SeverityBadge } from "./severity-badge"
import { useReviewFinding, useClause } from "@/lib/hooks/use-tasks"
import type { ClauseFlag } from "@/lib/types/api"
import { CheckCircle2, XCircle, BookOpen, ChevronDown, ChevronUp, Info, Library, FileText, Wrench, ArrowRight, Pencil, AlertTriangle, Target } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { libraryApi } from "@/lib/api/library"
import { PRIORITY_CONFIG } from "@/lib/types/api"
import { explainFinding } from "@/lib/finding-explain"

interface FindingDetailSheetProps {
  finding: ClauseFlag | null
  projectId: string
  open: boolean
  onOpenChange: (open: boolean) => void
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

export function FindingDetailSheet({ finding, projectId, open, onOpenChange }: FindingDetailSheetProps) {
  const [note, setNote] = useState("")
  const [showReasoning, setShowReasoning] = useState(false)
  const [showDetail, setShowDetail] = useState(false)
  const [addingToLibrary, setAddingToLibrary] = useState(false)
  const { mutate: review, isPending } = useReviewFinding(projectId)

  // Fetch the actual clause text the flag is pinned to
  const { data: clause, isLoading: clauseLoading } = useClause(
    projectId,
    finding?.clause_id ?? null,
  )

  function handleReview(status: "approved" | "rejected") {
    if (!finding) return
    review({ flagId: finding.id, data: { status, note: note || undefined } }, {
      onSuccess: () => { onOpenChange(false); setNote("") },
    })
  }

  async function handleAddToLibrary() {
    if (!finding || !clause) return
    setAddingToLibrary(true)
    try {
      await libraryApi.create({
        title: finding.title,
        body_text: clause.body_text,
        category: finding.flag_type,
        status: "approved",
      })
      toast.success("Added to Clause Library", {
        description: "The clause text is now saved in your organisation's library.",
      })
    } catch {
      toast.error("Failed to add to library", {
        description: "Clause library indexing is unavailable in demo mode.",
      })
    } finally {
      setAddingToLibrary(false)
    }
  }

  if (!finding) return null

  const isReviewed = finding.reviewer_status !== "pending"

  const hasChangeMarkup =
    clause &&
    (clause.has_tracked_insertion || clause.has_tracked_deletion ||
      clause.has_strikethrough || clause.has_comment)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
        <SheetHeader className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <SeverityBadge severity={finding.severity} />
            <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
              {flagTypeLabels[finding.flag_type] ?? finding.flag_type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
            </span>
          </div>
          <SheetTitle className="text-lg leading-snug">{finding.title}</SheetTitle>
          {finding.confidence != null && (
            <SheetDescription className="flex items-center gap-1.5">
              <span className="flex items-center gap-1">
                Confidence: {Math.round(finding.confidence * 100)}%
                <span className="relative group">
                  <Info className="w-3.5 h-3.5 text-slate-400 cursor-help" />
                  <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 rounded-lg bg-slate-900 px-3 py-2 text-xs text-slate-100 opacity-0 group-hover:opacity-100 transition-opacity z-50 shadow-lg">
                    How confident the AI is that this finding is a real issue. Higher % = stronger signal. Below 70% means the AI flagged it but is less certain — review carefully before acting.
                  </span>
                </span>
              </span>
              {finding.risk_score != null && (
                <span className="text-slate-400">· Risk Score: {finding.risk_score}/10</span>
              )}
            </SheetDescription>
          )}
        </SheetHeader>

        <div className="space-y-5">

          {/* ── In plain English: What changed / Why it matters / What to do ── */}
          {(() => {
            const ex = explainFinding(finding)
            return (
              <div className="rounded-xl border border-border bg-secondary/40 p-4 space-y-3">
                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-sev-medium-bg text-sev-medium">
                    <Pencil className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <p className="text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-muted-foreground">What changed</p>
                    <p className="mt-0.5 text-sm font-medium leading-snug text-foreground">{ex.whatChanged}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-sev-critical-bg text-sev-critical">
                    <AlertTriangle className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <p className="text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-muted-foreground">Why it matters</p>
                    <p className="mt-0.5 text-sm leading-relaxed text-foreground/90">{ex.whyItMatters}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-success-bg text-success">
                    <Target className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <p className="text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-muted-foreground">What to do</p>
                    <p className="mt-0.5 text-sm leading-relaxed text-foreground/90">{ex.whatToDo}</p>
                  </div>
                </div>
              </div>
            )
          })()}

          {/* ── Clause Text ── */}
          <div className="rounded-lg border border-slate-200 overflow-hidden">
            <div className="flex items-center gap-2 bg-slate-50 border-b border-slate-200 px-4 py-2.5">
              <FileText className="w-3.5 h-3.5 text-slate-500" />
              <h4 className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                {clause?.heading ? `Clause: ${clause.heading}` : "Flagged Clause Text"}
              </h4>
              {clause?.clause_number && (
                <span className="ml-auto text-xs text-slate-400">§{clause.clause_number}</span>
              )}
            </div>
            <div className="p-4">
              {clauseLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-5/6" />
                  <Skeleton className="h-3 w-4/6" />
                </div>
              ) : clause ? (
                <>
                  <p className="text-sm text-slate-800 leading-relaxed whitespace-pre-wrap">
                    {clause.body_text}
                  </p>
                  {hasChangeMarkup && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {clause.has_tracked_insertion && (
                        <span className="text-xs bg-green-100 text-green-700 border border-green-200 rounded px-2 py-0.5">+ Tracked insertion</span>
                      )}
                      {clause.has_tracked_deletion && (
                        <span className="text-xs bg-red-100 text-red-700 border border-red-200 rounded px-2 py-0.5">− Tracked deletion</span>
                      )}
                      {clause.has_strikethrough && (
                        <span className="text-xs bg-amber-100 text-amber-700 border border-amber-200 rounded px-2 py-0.5">Strikethrough text</span>
                      )}
                      {clause.has_comment && (
                        <span className="text-xs bg-blue-100 text-blue-700 border border-blue-200 rounded px-2 py-0.5">Has comment</span>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-slate-400 italic">Clause text not available.</p>
              )}
            </div>
          </div>

          {/* ── Suggested Fix (deterministic modification suggestion) ── */}
          {finding.suggestion && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 overflow-hidden">
              <div className="flex items-center gap-2 bg-emerald-100/60 border-b border-emerald-200 px-4 py-2.5">
                <Wrench className="w-3.5 h-3.5 text-emerald-700" />
                <h4 className="text-xs font-semibold text-emerald-800 uppercase tracking-wide">
                  Suggested Fix
                </h4>
                {finding.priority && (
                  <span className={cn(
                    "ml-auto inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border",
                    PRIORITY_CONFIG[finding.priority].bg,
                    PRIORITY_CONFIG[finding.priority].color,
                    PRIORITY_CONFIG[finding.priority].border,
                  )}>
                    <span className={cn("w-1.5 h-1.5 rounded-full", PRIORITY_CONFIG[finding.priority].dot)} />
                    {PRIORITY_CONFIG[finding.priority].label}
                  </span>
                )}
              </div>
              <div className="p-4 space-y-3">
                <div className="flex items-start gap-2 text-sm">
                  <span className="shrink-0 text-xs font-medium text-slate-500 uppercase tracking-wide pt-0.5 w-16">Current</span>
                  <span className="text-slate-700 line-through decoration-red-400/70">{finding.suggestion.original_text}</span>
                </div>
                <div className="flex items-start gap-2 text-sm">
                  <span className="shrink-0 text-xs font-medium text-emerald-600 uppercase tracking-wide pt-0.5 w-16 flex items-center gap-1">
                    <ArrowRight className="w-3 h-3" /> Fix
                  </span>
                  <span className="text-emerald-900 font-medium">{finding.suggestion.suggested_text}</span>
                </div>
                <div className="pt-2 border-t border-emerald-200/70">
                  <p className="text-xs text-emerald-800/90 leading-relaxed">
                    <span className="font-semibold">Why: </span>{finding.suggestion.reason}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Technical detail (collapsible) — raw engine output for analysts */}
          {finding.description && (
            <div>
              <button
                onClick={() => setShowDetail((v) => !v)}
                className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide hover:text-foreground transition-colors"
              >
                {showDetail ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                Technical detail
              </button>
              {showDetail && (
                <div className="mt-2 space-y-2 rounded-lg border border-border bg-secondary/30 p-3">
                  <p className="text-xs text-muted-foreground leading-relaxed">{finding.description}</p>
                  {finding.recommendation && (
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      <span className="font-semibold text-foreground/70">Recommendation: </span>{finding.recommendation}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Law Citation */}
          {finding.law_act_name && (
            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
              <div className="flex items-center gap-2 mb-2">
                <BookOpen className="w-4 h-4 text-blue-600" />
                <h4 className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Law Reference</h4>
              </div>
              <p className="text-sm font-medium text-blue-900">
                {finding.law_act_name}
                {finding.law_section_number && ` — ${finding.law_section_number}`}
              </p>
              {finding.law_jurisdiction && (
                <p className="text-xs text-blue-600 mt-0.5">Jurisdiction: {finding.law_jurisdiction}</p>
              )}
              {finding.law_retrieved_text && (
                <blockquote className="mt-3 pl-3 border-l-2 border-blue-300 text-xs text-blue-800 italic leading-relaxed">
                  {finding.law_retrieved_text}
                </blockquote>
              )}
            </div>
          )}

          {/* Reasoning trace (collapsible) */}
          {finding.reasoning_trace && (
            <div>
              <button
                onClick={() => setShowReasoning((v) => !v)}
                className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide hover:text-slate-700 transition-colors"
              >
                {showReasoning ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                AI Reasoning Trace
              </button>
              {showReasoning && (
                <p className="mt-2 text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-lg border font-mono">
                  {finding.reasoning_trace}
                </p>
              )}
            </div>
          )}

          {/* Add to Clause Library */}
          {clause && (
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
              <div className="flex items-center gap-2">
                <Library className="w-4 h-4 text-slate-400" />
                <span className="text-xs text-slate-600">Save this clause text to your organisation&apos;s Clause Library</span>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={handleAddToLibrary}
                disabled={addingToLibrary}
                className="shrink-0 text-xs h-7"
              >
                {addingToLibrary ? "Saving…" : "Add to Library"}
              </Button>
            </div>
          )}

          {/* Previous review */}
          {isReviewed && (
            <div className={cn(
              "p-3 rounded-lg border text-sm",
              finding.reviewer_status === "approved" ? "bg-green-50 border-green-200 text-green-800" : "bg-red-50 border-red-200 text-red-800"
            )}>
              <p className="font-medium capitalize">{finding.reviewer_status}</p>
              {finding.reviewer_note && <p className="mt-1 text-xs opacity-80">{finding.reviewer_note}</p>}
            </div>
          )}

          {/* Review form */}
          {!isReviewed && (
            <div className="pt-4 border-t space-y-3">
              <div className="space-y-1.5">
                <Label>Reviewer Note <span className="text-slate-400 font-normal">(optional)</span></Label>
                <Textarea
                  placeholder="Add context or justification for your decision…"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  rows={3}
                />
              </div>
              <div className="flex gap-2">
                <Button
                  className="flex-1 bg-green-600 hover:bg-green-700"
                  onClick={() => handleReview("approved")}
                  disabled={isPending}
                >
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  Approve
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={() => handleReview("rejected")}
                  disabled={isPending}
                >
                  <XCircle className="w-4 h-4 mr-2" />
                  Reject
                </Button>
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
