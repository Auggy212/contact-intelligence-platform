import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { ProjectStatus } from "@/lib/types/api"

const statusConfig: Record<ProjectStatus, { label: string; className: string }> = {
  draft: { label: "Draft", className: "bg-slate-100 text-slate-600 border-slate-300" },
  processing: { label: "Processing", className: "bg-blue-100 text-blue-700 border-blue-300" },
  completed: { label: "Completed", className: "bg-green-100 text-green-700 border-green-300" },
  failed: { label: "Failed", className: "bg-red-100 text-red-700 border-red-300" },
}

export function ProjectStatusBadge({ status }: { status: ProjectStatus }) {
  const { label, className } = statusConfig[status]
  return (
    <Badge variant="outline" className={cn("text-xs font-medium", className)}>
      {label}
    </Badge>
  )
}
