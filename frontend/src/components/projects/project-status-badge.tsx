import { cn } from "@/lib/utils"
import type { ProjectStatus } from "@/lib/types/api"

const statusConfig: Record<ProjectStatus, { label: string; dot: string; className: string }> = {
  draft:      { label: "Draft",      dot: "bg-zinc-500",   className: "bg-zinc-800/60 text-zinc-400 border-zinc-700/60" },
  processing: { label: "Processing", dot: "bg-orange-400 animate-pulse", className: "bg-orange-500/10 text-orange-400 border-orange-500/20" },
  completed:  { label: "Completed",  dot: "bg-emerald-400", className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
  failed:     { label: "Failed",     dot: "bg-red-400",    className: "bg-red-500/10 text-red-400 border-red-500/20" },
}

export function ProjectStatusBadge({ status }: { status: ProjectStatus }) {
  const { label, dot, className } = statusConfig[status]
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold", className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
      {label}
    </span>
  )
}
