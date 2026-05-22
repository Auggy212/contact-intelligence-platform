import { apiClient } from "./client"
import type { ChecklistRule, ChecklistRuleCreate, ChecklistRuleUpdate } from "@/lib/types/api"

export const checklistApi = {
  list: (): Promise<ChecklistRule[]> =>
    apiClient.get("/checklist-rules").then((r) => r.data),

  get: (id: string): Promise<ChecklistRule> =>
    apiClient.get(`/checklist-rules/${id}`).then((r) => r.data),

  create: (data: ChecklistRuleCreate): Promise<ChecklistRule> =>
    apiClient.post("/checklist-rules", data).then((r) => r.data),

  update: (id: string, data: ChecklistRuleUpdate): Promise<ChecklistRule> =>
    apiClient.patch(`/checklist-rules/${id}`, data).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/checklist-rules/${id}`).then(() => undefined),
}
