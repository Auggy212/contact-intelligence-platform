"use client"

import { useState } from "react"
import { Plus, FolderOpen, Search, Scale, Sparkles, CheckCircle2, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { EmptyState } from "@/components/shared/empty-state"
import { ProjectCard } from "@/components/projects/project-card"
import { CreateProjectDialog } from "@/components/projects/create-project-dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { useProjects } from "@/lib/hooks/use-projects"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { ProjectStatus } from "@/lib/types/api"
import { cn } from "@/lib/utils"

export default function ProjectsPage() {
  const [createOpen, setCreateOpen] = useState(false)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | "all">("all")
  const { data: projects, isLoading } = useProjects()

  const all = projects ?? []
  const filtered = all.filter((p) => {
    const matchesSearch = p.name.toLowerCase().includes(search.toLowerCase())
    const matchesStatus = statusFilter === "all" || p.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const activeCount = all.filter((p) => p.status === "processing").length
  const doneCount = all.filter((p) => p.status === "completed").length

  return (
    <div>
      {/* ── Hero band ("The Lens") ── */}
      <div className="animate-rise-blur relative mb-8 overflow-hidden rounded-2xl border border-border surface-glass shadow-lg">
        {/* Ambient amber + cool glow, drifting */}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/[0.12] via-transparent to-transparent" />
        <div className="animate-float pointer-events-none absolute -right-20 -top-24 h-72 w-72 rounded-full bg-primary/20 blur-3xl" />
        <div className="animate-float pointer-events-none absolute -bottom-28 right-1/3 h-56 w-56 rounded-full bg-[hsl(232_80%_60%/0.14)] blur-3xl [animation-delay:3s]" />
        {/* Hairline top highlight */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />

        <div className="relative flex flex-col gap-6 p-6 lg:flex-row lg:items-end lg:justify-between lg:p-8">
          <div className="max-w-xl">
            <div className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/[0.08] px-2.5 py-1 text-xs font-medium tracking-wide text-primary">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping-amber absolute inline-flex h-full w-full rounded-full bg-primary opacity-70" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
              </span>
              Deterministic contract intelligence
            </div>
            <h1 className="flex items-center gap-3 text-3xl font-bold tracking-[-0.03em] text-foreground text-balance sm:text-[2.5rem] sm:leading-[1.05]">
              <span className="scan-line flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-[hsl(42_100%_62%)] to-[hsl(32_96%_48%)] text-[hsl(40_60%_10%)] shadow-[0_6px_20px_-4px_hsl(38_96%_56%/0.6)]">
                <Scale className="h-6 w-6" strokeWidth={2.4} />
              </span>
              Your contract reviews
            </h1>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-muted-foreground text-pretty">
              Compare drafts against your template, catch Indian-law risks, and export a review memo — all offline, fully auditable.
            </p>
          </div>

          {/* Live portfolio stats + primary action */}
          <div className="flex items-center gap-3">
            <HeroStat icon={FolderOpen} value={all.length} label="Projects" />
            <HeroStat icon={Loader2} value={activeCount} label="Active" tone="primary" />
            <HeroStat icon={CheckCircle2} value={doneCount} label="Completed" tone="success" />
            <Button onClick={() => setCreateOpen(true)} className="ml-1 h-11 shadow-glow">
              <Plus className="mr-2 h-4 w-4" />
              New Project
            </Button>
          </div>
        </div>
      </div>

      <div className="mb-6 flex gap-3">
        <div className="relative max-w-xs flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/70" />
          <Input
            placeholder="Search projects…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as ProjectStatus | "all")}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="processing">Processing</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-lg" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={FolderOpen}
          title={search || statusFilter !== "all" ? "No projects match your filters" : "No projects yet"}
          description={search || statusFilter !== "all" ? "Try adjusting your search or filters" : "Create your first contract review project to get started"}
          action={(!search && statusFilter === "all") ? { label: "New Project", onClick: () => setCreateOpen(true) } : undefined}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((project, i) => (
            <div
              key={project.id}
              className="animate-rise-blur"
              style={{ animationDelay: `${Math.min(i * 55, 440)}ms` }}
            >
              <ProjectCard project={project} />
            </div>
          ))}
        </div>
      )}

      <CreateProjectDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  )
}

function HeroStat({
  icon: Icon,
  value,
  label,
  tone = "ink",
}: {
  icon: typeof FolderOpen
  value: number
  label: string
  tone?: "ink" | "primary" | "success"
}) {
  const valueClass =
    tone === "primary" ? "text-primary" : tone === "success" ? "text-success" : "text-foreground"
  return (
    <div className="hidden min-w-[84px] rounded-xl border border-border bg-card/60 px-3.5 py-2.5 text-center backdrop-blur-sm sm:block">
      <div className="flex items-center justify-center gap-1.5">
        <Icon className={cn("h-3.5 w-3.5", valueClass)} />
        <span className={cn("text-xl font-bold tabular-nums", valueClass)}>{value}</span>
      </div>
      <p className="mt-0.5 text-[0.7rem] text-muted-foreground">{label}</p>
    </div>
  )
}
