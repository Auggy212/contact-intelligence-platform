"use client"

import { useState } from "react"
import Link from "next/link"
import { useConcepts, useLawCorpus } from "@/lib/hooks/use-transparency"
import { useChecklist } from "@/lib/hooks/use-checklist"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { SeverityBadge } from "@/components/findings/severity-badge"
import { cn } from "@/lib/utils"
import type { Severity } from "@/lib/types/api"
import type { LawCheck } from "@/lib/api/transparency"
import { Eye, Scale, Sparkles, CheckSquare, ChevronDown, ChevronRight, ArrowRight, BookOpen } from "lucide-react"

type Section = "concepts" | "laws" | "rules"

const asSeverity = (s: string): Severity =>
  (["critical", "high", "medium", "low", "info"].includes(s) ? s : "info") as Severity

export default function WhatWeCheckPage() {
  const [section, setSection] = useState<Section>("concepts")
  const { data: concepts, isLoading: cLoading } = useConcepts()
  const { data: corpus, isLoading: lLoading } = useLawCorpus()
  const { data: rules, isLoading: rLoading } = useChecklist()

  const conceptCount = concepts?.total ?? 0
  const lawCount = corpus?.total_checks ?? 0
  const actCount = corpus?.total_acts ?? 0
  const ruleCount = rules?.length ?? 0

  return (
    <div className="space-y-6 animate-rise-blur">
      {/* ── Hero band ── */}
      <div className="relative overflow-hidden rounded-2xl border border-border surface-glass shadow-lg">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/[0.12] via-transparent to-transparent" />
        <div className="animate-float pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-primary/20 blur-3xl" />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
        <div className="relative p-6 lg:p-8">
          <div className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/[0.08] px-2.5 py-1 text-xs font-medium tracking-wide text-primary">
            <Sparkles className="h-3 w-3" />
            Full transparency
          </div>
          <h1 className="flex items-center gap-3 text-3xl font-bold tracking-[-0.03em] text-foreground text-balance sm:text-[2.5rem] sm:leading-[1.05]">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-[hsl(42_100%_62%)] to-[hsl(32_96%_48%)] text-[hsl(40_60%_10%)] shadow-[0_6px_20px_-4px_hsl(38_96%_56%/0.6)]">
              <Eye className="h-6 w-6" strokeWidth={2.4} />
            </span>
            What every analysis checks
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground text-pretty">
            Nothing here is a black box. Every contract you upload is checked against these exact
            concepts, laws, and your own rules — shown in full so you always know the basis of a finding.
            When the engine or your rules change, this page updates automatically.
          </p>

          {/* Live counts */}
          <div className="mt-6 flex flex-wrap gap-3">
            <CountPill icon={Sparkles} value={conceptCount} label="Semantic concepts" />
            <CountPill icon={Scale} value={lawCount} label={`Law checks · ${actCount} acts`} />
            <CountPill icon={CheckSquare} value={ruleCount} label="Your checklist rules" />
          </div>
        </div>
      </div>

      {/* ── Section tabs ── */}
      <Tabs value={section} onValueChange={(v) => setSection(v as Section)}>
        <TabsList>
          <TabsTrigger value="concepts">Concepts ({conceptCount})</TabsTrigger>
          <TabsTrigger value="laws">Indian Law ({lawCount})</TabsTrigger>
          <TabsTrigger value="rules">Your Rules ({ruleCount})</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* ── Concepts ── */}
      {section === "concepts" && (
        <div className="space-y-3">
          <SectionIntro
            title="Semantic concepts"
            body="Meaning-level checks the engine detects when comparing your draft to the template — not keyword matching. Each one is a known contract risk with a recommended action."
          />
          {cLoading ? (
            <SkeletonGrid />
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {concepts?.concepts.map((c, i) => (
                <Card key={c.name + i} className="p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <SeverityBadge severity={asSeverity(c.severity)} />
                    {c.risk_score != null && (
                      <span className="ml-auto text-xs text-muted-foreground tabular-nums">risk {c.risk_score}/10</span>
                    )}
                  </div>
                  <p className="text-sm font-semibold text-foreground">{c.name}</p>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{c.recommendation}</p>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Laws ── */}
      {section === "laws" && (
        <div className="space-y-4">
          <SectionIntro
            title="Indian-law corpus"
            body="The statutes and sections every contract is validated against. These are the actual law books the analysis relies on — grouped by act, with the statutory text behind each check."
          />
          {lLoading ? (
            <SkeletonGrid />
          ) : (
            <div className="space-y-3">
              {corpus?.acts.map((act) => (
                <LawActGroup key={act.act_name} actName={act.act_name} count={act.count} checks={act.checks} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Your rules ── */}
      {section === "rules" && (
        <div className="space-y-3">
          <SectionIntro
            title="Your organisation's checklist rules"
            body="Business rules your team defined — run on every analysis alongside the concepts and laws above. Add, edit, or disable them any time; changes apply to the next analysis."
            action={
              <Button asChild variant="outline" size="sm">
                <Link href="/checklist"><ArrowRight className="mr-1.5 h-3.5 w-3.5" />Manage rules</Link>
              </Button>
            }
          />
          {rLoading ? (
            <SkeletonGrid />
          ) : ruleCount === 0 ? (
            <Card className="p-8 text-center">
              <CheckSquare className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
              <p className="text-sm font-medium text-foreground">No custom rules yet</p>
              <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
                Add your company&apos;s own rules — payment caps, mandatory clauses, jurisdiction requirements — and they run automatically.
              </p>
              <Button asChild className="mt-4" size="sm">
                <Link href="/checklist">Add your first rule</Link>
              </Button>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {rules?.map((r) => (
                <Card key={r.id} className={cn("p-4", !r.is_enabled && "opacity-55")}>
                  <div className="mb-2 flex items-center gap-2">
                    <SeverityBadge severity={asSeverity(r.severity)} />
                    <span className="rounded-full bg-secondary px-2 py-0.5 text-[0.7rem] font-medium text-muted-foreground">
                      {r.is_default ? "Default" : "Custom"}
                    </span>
                    {!r.is_enabled && (
                      <span className="ml-auto text-xs text-muted-foreground">Disabled</span>
                    )}
                  </div>
                  <p className="text-sm font-semibold text-foreground">{r.name}</p>
                  {r.description && (
                    <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{r.description}</p>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function CountPill({ icon: Icon, value, label }: { icon: typeof Eye; value: number; label: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-border bg-card/60 px-3.5 py-2 backdrop-blur-sm">
      <Icon className="h-4 w-4 text-primary" />
      <span className="text-lg font-bold text-foreground tabular-nums">{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  )
}

function SectionIntro({ title, body, action }: { title: string; body: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h2 className="text-lg font-semibold tracking-[-0.01em] text-foreground">{title}</h2>
        <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground text-pretty">{body}</p>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}

function LawActGroup({ actName, count, checks }: { actName: string; count: number; checks: LawCheck[] }) {
  const [open, setOpen] = useState(false)
  return (
    <Card className="overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-secondary/40"
      >
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <BookOpen className="h-4 w-4" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold text-foreground">{actName}</span>
          <span className="block text-xs text-muted-foreground">{count} check{count !== 1 ? "s" : ""}</span>
        </span>
        {open ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
      </button>
      {open && (
        <div className="divide-y divide-border/60 border-t border-border">
          {checks.map((c) => (
            <div key={c.id} className="px-4 py-3">
              <div className="mb-1.5 flex flex-wrap items-center gap-2">
                <SeverityBadge severity={asSeverity(c.severity)} />
                <span className="text-xs font-medium text-primary">{c.section}</span>
              </div>
              <p className="text-sm font-medium text-foreground">{c.title}</p>
              {c.law_text && (
                <p className="mt-1.5 border-l-2 border-border pl-3 text-xs italic leading-relaxed text-muted-foreground">
                  {c.law_text}
                </p>
              )}
              {c.recommendation && (
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                  <span className="font-semibold text-foreground/80">Recommendation: </span>{c.recommendation}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
    </div>
  )
}
