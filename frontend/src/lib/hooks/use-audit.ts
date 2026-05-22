import { useQuery } from "@tanstack/react-query"
import { auditApi } from "@/lib/api/audit"

export function useAuditLog(skip = 0, limit = 50, action?: string) {
  return useQuery({
    queryKey: ["audit-log", skip, limit, action],
    queryFn: () => auditApi.list(skip, limit, action),
  })
}
