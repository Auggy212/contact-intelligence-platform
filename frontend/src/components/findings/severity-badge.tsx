import { cn } from "@/lib/utils"
import { SEVERITY_CONFIG } from "@/lib/types/api"
import type { Severity } from "@/lib/types/api"

export function SeverityBadge({ severity }: { severity: Severity }) {
  const cfg = SEVERITY_CONFIG[severity]
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border", cfg.bg, cfg.color, cfg.border)}>
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", cfg.dot)} />
      {cfg.label}
    </span>
  )
}
