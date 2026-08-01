import { useQuery } from "@tanstack/react-query"
import { auditApi } from "@/lib/api/audit"

export function useAuditLog(skip = 0, limit = 50, action?: string) {
  return useQuery({
    queryKey: ["audit-log", skip, limit, action],
    queryFn: () => auditApi.list(skip, limit, action),
  })
}

export function useProjectAudit(projectId: string, limit = 5) {
  return useQuery({
    queryKey: ["audit-log", "project", projectId, limit],
    queryFn: () => auditApi.list(0, limit, undefined, projectId),
    enabled: !!projectId,
  })
}
