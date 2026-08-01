"use client"

import { useEffect, useMemo, useRef, useState, useCallback } from "react"
import { renderAsync } from "docx-preview"
import { useDocuments, useDocumentContent, useFileClauses } from "@/lib/hooks/use-documents"
import { useFindings } from "@/lib/hooks/use-tasks"
import { SeverityBadge } from "@/components/findings/severity-badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { FILE_ROLE_LABELS, type FileRole, type ClauseFlag, type Severity } from "@/lib/types/api"
import type { FileClause } from "@/lib/api/documents"
import { explainFinding } from "@/lib/finding-explain"
import {
  FileText, ShieldCheck, AlertTriangle, Crosshair, Info, Loader2,
} from "lucide-react"

interface DocumentVerifyViewProps {
  projectId: string
}

const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0, high: 1, medium: 2, low: 3, info: 4,
}

// Normalise text so DOM text and clause body_text can be compared
// (collapse whitespace, drop punctuation differences that docx rendering introduces)
function normalize(text: string): string {
  return text.toLowerCase().replace(/\s+/g, " ").replace(/[^\w\s]/g, "").trim()
}

export function DocumentVerifyView({ projectId }: DocumentVerifyViewProps) {
  const { data: documents } = useDocuments(projectId)
  const { data: findings } = useFindings(projectId)

  // Which uploaded file is shown. Default to B (the proposed draft most findings target).
  const [activeRole, setActiveRole] = useState<FileRole>("B")

  const availableRoles = useMemo<FileRole[]>(() => {
    const roles = (documents ?? [])
      .filter((d) => d.parse_status === "completed")
      .map((d) => d.file_role)
    return (["A", "B", "C"] as FileRole[]).filter((r) => roles.includes(r))
  }, [documents])

  // Ensure activeRole is one that actually exists
  useEffect(() => {
    if (availableRoles.length && !availableRoles.includes(activeRole)) {
      setActiveRole(availableRoles[0])
    }
  }, [availableRoles, activeRole])

  const activeFile = useMemo(
    () => documents?.find((d) => d.file_role === activeRole) ?? null,
    [documents, activeRole]
  )
  const fileId = activeFile?.id ?? null

  const { data: fileBytes, isLoading: bytesLoading, isError: bytesError } =
    useDocumentContent(projectId, fileId)
  const { data: clauses } = useFileClauses(projectId, fileId)

  const renderRef = useRef<HTMLDivElement>(null)
  const [rendered, setRendered] = useState(false)
  const [activeFindingId, setActiveFindingId] = useState<string | null>(null)

  // Findings that belong to clauses in the currently-shown file.
  // A finding's clause_id points to a ParsedClause; we keep only those whose
  // clause is in this file (so File B shows B's findings, etc.).
  const clauseIds = useMemo(
    () => new Set((clauses ?? []).map((c) => c.id)),
    [clauses]
  )
  const fileFindings = useMemo(() => {
    const list = (findings ?? []).filter(
      (f) => clauseIds.has(f.clause_id) || (f.source_clause_id && clauseIds.has(f.source_clause_id))
    )
    return [...list].sort(
      (a, b) =>
        (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9) ||
        (b.risk_score ?? 0) - (a.risk_score ?? 0)
    )
  }, [findings, clauseIds])

  const clauseById = useMemo(() => {
    const m = new Map<string, FileClause>()
    for (const c of clauses ?? []) m.set(c.id, c)
    return m
  }, [clauses])

  // ── Render the DOCX into the container ──────────────────────────────────────
  useEffect(() => {
    setRendered(false)
    const container = renderRef.current
    if (!container || !fileBytes) return
    container.innerHTML = ""
    let cancelled = false
    renderAsync(fileBytes, container, undefined, {
      className: "docx",
      inWrapper: true,
      ignoreWidth: false,
      ignoreHeight: false,
      breakPages: true,
      experimental: true,
      renderHeaders: true,
      renderFooters: true,
    })
      .then(() => {
        if (!cancelled) setRendered(true)
      })
      .catch(() => {
        if (!cancelled) setRendered(false)
      })
    return () => {
      cancelled = true
    }
  }, [fileBytes])

  // ── Highlight + scroll to a clause in the rendered document ─────────────────
  const clearHighlights = useCallback(() => {
    const container = renderRef.current
    if (!container) return
    container.querySelectorAll("[data-verify-highlight]").forEach((el) => {
      el.removeAttribute("data-verify-highlight")
      ;(el as HTMLElement).style.backgroundColor = ""
      ;(el as HTMLElement).style.outline = ""
      ;(el as HTMLElement).style.borderRadius = ""
    })
  }, [])

  const highlightClause = useCallback(
    (clause: FileClause | undefined) => {
      const container = renderRef.current
      if (!container || !clause) return false
      clearHighlights()

      // docx-preview renders each paragraph as a <p>. We find the paragraph(s)
      // whose text matches the start of the clause body (or its heading).
      const paragraphs = Array.from(
        container.querySelectorAll("p, h1, h2, h3, h4, li, td")
      ) as HTMLElement[]

      const targetSnippets: string[] = []
      if (clause.heading) targetSnippets.push(normalize(clause.heading))
      // first ~12 words of the body is a robust matching key
      const bodyKey = normalize(clause.body_text).split(" ").slice(0, 12).join(" ")
      if (bodyKey) targetSnippets.push(bodyKey)

      let firstMatch: HTMLElement | null = null
      for (const p of paragraphs) {
        const ptext = normalize(p.textContent ?? "")
        if (!ptext) continue
        const hit = targetSnippets.some(
          (snip) => snip.length > 6 && (ptext.includes(snip) || snip.includes(ptext))
        )
        if (hit) {
          p.setAttribute("data-verify-highlight", "1")
          p.style.backgroundColor = "rgba(250, 204, 21, 0.35)" // yellow
          p.style.outline = "2px solid rgba(234, 179, 8, 0.9)"
          p.style.borderRadius = "3px"
          if (!firstMatch) firstMatch = p
        }
      }

      if (firstMatch) {
        firstMatch.scrollIntoView({ behavior: "smooth", block: "center" })
        return true
      }
      return false
    },
    [clearHighlights]
  )

  // When a finding is clicked, locate + highlight its clause
  const handleFindingClick = useCallback(
    (finding: ClauseFlag) => {
      setActiveFindingId(finding.id)
      const clause =
        clauseById.get(finding.clause_id) ??
        (finding.source_clause_id ? clauseById.get(finding.source_clause_id) : undefined)
      const ok = highlightClause(clause)
      if (!ok) {
        // No DOM match — clear so the user isn't misled by a stale highlight
        clearHighlights()
      }
    },
    [clauseById, highlightClause, clearHighlights]
  )

  // ── Empty / loading states ──────────────────────────────────────────────────
  if (documents && documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <FileText className="w-10 h-10 text-slate-300 mb-3" />
        <p className="text-slate-500">No documents uploaded yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Trust banner */}
      <div className="flex items-start gap-2.5 rounded-lg border border-success-border bg-success-bg p-3.5 text-sm text-success">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
        <span className="text-pretty text-success/90">
          This is your <strong className="font-semibold text-success">original uploaded document</strong>, rendered untouched. Click any
          finding on the right to highlight exactly where it occurs in the document — so you can
          verify every claim against the real text.
        </span>
      </div>

      {/* File selector */}
      <div className="flex items-center gap-2">
        {availableRoles.map((role) => {
          const info = FILE_ROLE_LABELS[role]
          const isActive = role === activeRole
          return (
            <button
              key={role}
              onClick={() => {
                setActiveRole(role)
                setActiveFindingId(null)
              }}
              className={cn(
                "rounded-lg border px-3 py-1.5 text-sm font-medium transition-all duration-150 ease-out-quint",
                isActive
                  ? "border-primary bg-primary text-primary-foreground shadow-sm"
                  : "border-border bg-card text-muted-foreground hover:border-border hover:text-foreground",
              )}
            >
              {role} · {info.label}
            </button>
          )
        })}
      </div>

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[1fr_360px]">
        {/* ── Left: rendered document ── */}
        <div className="overflow-hidden rounded-lg border border-border bg-secondary shadow-sm">
          <div className="flex items-center gap-2 border-b border-border bg-card px-4 py-2.5">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="truncate text-sm font-medium text-foreground">
              {activeFile?.original_filename ?? "Document"}
            </span>
            {rendered && (
              <span className="ml-auto flex items-center gap-1 text-xs text-success">
                <ShieldCheck className="h-3.5 w-3.5" /> Original, unmodified
              </span>
            )}
          </div>
          <div className="h-[70vh] overflow-y-auto bg-secondary/50 p-4">
            {bytesLoading && (
              <div className="space-y-3 bg-white p-8 rounded shadow-sm max-w-3xl mx-auto">
                <Skeleton className="h-5 w-1/2" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-4/5" />
                <div className="h-3" />
                <Skeleton className="h-5 w-1/3" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-5/6" />
              </div>
            )}
            {bytesError && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <AlertTriangle className="w-8 h-8 text-amber-500 mb-2" />
                <p className="text-sm text-slate-600">Could not load the document for preview.</p>
              </div>
            )}
            {!bytesLoading && !bytesError && fileBytes && !rendered && (
              <div className="flex items-center justify-center py-16 text-slate-500 text-sm gap-2">
                <Loader2 className="w-4 h-4 animate-spin" /> Rendering document…
              </div>
            )}
            {/* docx-preview mounts here. Force TRUE white paper + dark ink for
                the rendered document regardless of the app's dark theme — a
                contract should look like a real printed page, and this keeps its
                text fully legible (the compat layer must not tint it). */}
            <div
              ref={renderRef}
              className="verify-docx-container"
            />
          </div>
        </div>

        {/* ── Right: findings panel ── */}
        <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
          <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
            <Crosshair className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium text-foreground">
              Findings in this document
            </span>
            <span className="ml-auto rounded-full bg-secondary px-2 py-0.5 text-xs font-medium text-muted-foreground tabular-nums">
              {fileFindings.length}
            </span>
          </div>

          <div className="max-h-[70vh] divide-y divide-border/70 overflow-y-auto">
            {!findings && (
              <div className="space-y-3 p-4">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            )}

            {findings && fileFindings.length === 0 && (
              <div className="flex flex-col items-center justify-center px-4 py-12 text-center">
                <Info className="mb-2 h-7 w-7 text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground">
                  No findings target this document. Try another file (A / B / C) above.
                </p>
              </div>
            )}

            {fileFindings.map((finding) => {
              const clause =
                clauseById.get(finding.clause_id) ??
                (finding.source_clause_id ? clauseById.get(finding.source_clause_id) : undefined)
              const isActive = finding.id === activeFindingId
              const vcList = Array.isArray(finding.value_changes)
                ? (finding.value_changes as unknown as Array<{
                    old_display?: string
                    new_display?: string
                    label?: string
                  }>)
                : []
              const firstVc = vcList[0]
              const ex = explainFinding(finding)
              return (
                <button
                  key={finding.id}
                  onClick={() => handleFindingClick(finding)}
                  className={cn(
                    "relative w-full px-4 py-3 text-left transition-colors duration-150 ease-out-quint hover:bg-secondary/50",
                    isActive && "bg-sev-medium-bg hover:bg-sev-medium-bg",
                  )}
                >
                  {/* Active indicator */}
                  <span
                    className={cn(
                      "absolute left-0 top-0 h-full w-0.5 bg-sev-medium transition-opacity",
                      isActive ? "opacity-100" : "opacity-0",
                    )}
                  />
                  <div className="mb-1 flex items-center gap-2">
                    <SeverityBadge severity={finding.severity} />
                    {clause?.heading && (
                      <span className="truncate text-xs text-muted-foreground">{clause.heading}</span>
                    )}
                  </div>
                  <p className="line-clamp-2 text-sm font-medium leading-snug text-foreground">
                    {ex.whatChanged}
                  </p>
                  {firstVc?.old_display && firstVc?.new_display && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      <span className="text-sev-critical line-through">{firstVc.old_display}</span>
                      {" → "}
                      <span className="font-medium text-success">{firstVc.new_display}</span>
                    </p>
                  )}
                  {/* One-line "why it matters" so a non-lawyer understands the risk */}
                  <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                    {ex.whyItMatters}
                  </p>
                  {isActive ? (
                    <p className="mt-1.5 flex items-center gap-1 text-xs font-medium text-sev-medium">
                      <Crosshair className="h-3 w-3" /> Highlighted in document
                    </p>
                  ) : (
                    <p className="mt-1.5 flex items-center gap-1 text-xs text-muted-foreground/70">
                      <Crosshair className="h-3 w-3" /> Click to locate in document
                    </p>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
