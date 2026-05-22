import { apiClient } from "./client"
import type { AuditLog } from "@/lib/types/api"

export const auditApi = {
  list: (skip = 0, limit = 50, action?: string): Promise<AuditLog[]> =>
    apiClient.get("/audit-log", { params: { skip, limit, ...(action ? { action } : {}) } }).then((r) => r.data),
}
