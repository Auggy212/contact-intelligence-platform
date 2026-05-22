import { apiClient } from "./client"
import type { AnalysisTask, ClauseFlag, TaskTriggerRequest, ReviewFlagRequest, Severity, FlagType } from "@/lib/types/api"

export const tasksApi = {
  trigger: (projectId: string, data: TaskTriggerRequest): Promise<AnalysisTask[]> =>
    apiClient.post(`/projects/${projectId}/tasks`, data).then((r) => r.data),

  getTask: (taskId: string): Promise<AnalysisTask> =>
    apiClient.get(`/tasks/${taskId}`).then((r) => r.data),

  getFindings: (
    projectId: string,
    filters?: { flag_type?: FlagType; severity?: Severity; reviewer_status?: string }
  ): Promise<ClauseFlag[]> =>
    apiClient.get(`/projects/${projectId}/findings`, { params: filters }).then((r) => r.data),

  reviewFinding: (flagId: string, data: ReviewFlagRequest): Promise<ClauseFlag> =>
    apiClient.patch(`/findings/${flagId}/review`, data).then((r) => r.data),
}
