import { cn } from "@/lib/utils"
import { SEVERITY_CONFIG } from "@/lib/types/api"
import type { Severity } from "@/lib/types/api"

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  const cfg = SEVERITY_CONFIG[severity]
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium",
        cfg.bg, cfg.color, cfg.border,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", cfg.dot)} />
      {cfg.label}
    </span>
  )
}
