import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
  className?: string
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-20 text-center", className)}>
      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-orange-500/15 bg-orange-500/8">
        <Icon className="h-7 w-7 text-orange-400" />
      </div>
      <h3 className="text-base font-bold text-white">{title}</h3>
      {description && <p className="mt-2 max-w-sm text-sm leading-relaxed text-zinc-500">{description}</p>}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-5 flex items-center gap-2 rounded-xl bg-orange-500 px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-orange-500/20 transition-all hover:bg-orange-400 active:scale-[0.97]"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
