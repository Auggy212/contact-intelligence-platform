import { apiClient } from "./client"
import type { AuditLog } from "@/lib/types/api"

export const auditApi = {
  list: (skip = 0, limit = 50, action?: string, resource_id?: string): Promise<AuditLog[]> =>
    apiClient.get("/audit-log", {
      params: { skip, limit, ...(action ? { action } : {}), ...(resource_id ? { resource_id } : {}) },
    }).then((r) => r.data),
}
