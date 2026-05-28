"use client"

import { useState } from "react"
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { SeverityBadge } from "./severity-badge"
import { useReviewFinding } from "@/lib/hooks/use-tasks"
import type { ClauseFlag } from "@/lib/types/api"
import { CheckCircle2, XCircle, BookOpen, ChevronDown, ChevronUp, Info } from "lucide-react"
import { cn } from "@/lib/utils"

interface FindingDetailSheetProps {
  finding: ClauseFlag | null
  projectId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

const flagTypeLabels: Record<string, string> = {
  missing_clause: "Missing Clause",
  weakened_clause: "Weakened Clause",
  modified: "Modified",
  deleted: "Deleted",
  added: "Added",
  law_violation: "Law Violation",
  law_at_risk: "Law Risk",
  checklist_fail: "Checklist Fail",
  checklist_not_found: "Checklist Not Found",
}

export function FindingDetailSheet({ finding, projectId, open, onOpenChange }: FindingDetailSheetProps) {
  const [note, setNote] = useState("")
  const [showReasoning, setShowReasoning] = useState(false)
  const { mutate: review, isPending } = useReviewFinding(projectId)

  function handleReview(status: "approved" | "rejected") {
    if (!finding) return
    review({ flagId: finding.id, data: { status, note: note || undefined } }, {
      onSuccess: () => { onOpenChange(false); setNote("") },
    })
  }

  if (!finding) return null

  const isReviewed = finding.reviewer_status !== "pending"

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
        <SheetHeader className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <SeverityBadge severity={finding.severity} />
            <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
              {flagTypeLabels[finding.flag_type] ?? finding.flag_type}
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
          {/* Description */}
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Description</h4>
            <p className="text-sm text-slate-700 leading-relaxed">{finding.description}</p>
          </div>

          {/* Recommendation */}
          {finding.recommendation && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Recommendation</h4>
              <p className="text-sm text-slate-700 leading-relaxed">{finding.recommendation}</p>
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
