import { apiClient } from "./client"
import type { AnalysisTask, ClauseFlag, TaskTriggerRequest, ReviewFlagRequest, Severity, FlagType, ModificationsResponse } from "@/lib/types/api"

export interface ParsedClause {
  id: string
  heading: string | null
  clause_number: string | null
  body_text: string
  paragraph_index: number
  has_tracked_insertion: boolean
  has_tracked_deletion: boolean
  has_strikethrough: boolean
  has_comment: boolean
}

export const tasksApi = {
  trigger: (projectId: string, data: TaskTriggerRequest): Promise<AnalysisTask[]> =>
    apiClient.post(`/projects/${projectId}/tasks`, data).then((r) => r.data),

  getTask: (taskId: string): Promise<AnalysisTask> =>
    apiClient.get(`/tasks/${taskId}`).then((r) => r.data),

  listProjectTasks: (projectId: string): Promise<AnalysisTask[]> =>
    apiClient.get(`/projects/${projectId}/tasks-list`).then((r) => r.data),

  getClause: (projectId: string, clauseId: string): Promise<ParsedClause> =>
    apiClient.get(`/projects/${projectId}/clauses/${clauseId}`).then((r) => r.data),

  getFindings: (
    projectId: string,
    filters?: { flag_type?: FlagType; severity?: Severity; reviewer_status?: string }
  ): Promise<ClauseFlag[]> =>
    apiClient.get(`/projects/${projectId}/findings`, { params: filters }).then((r) => r.data),

  reviewFinding: (flagId: string, data: ReviewFlagRequest): Promise<ClauseFlag> =>
    apiClient.patch(`/findings/${flagId}/review`, data).then((r) => r.data),

  getModifications: (projectId: string): Promise<ModificationsResponse> =>
    apiClient.get(`/projects/${projectId}/modifications`).then((r) => r.data),

  // Phase 6: semantically-related clauses in the same contract for a finding.
  getSimilarClauses: (
    projectId: string,
    flagId: string,
  ): Promise<SimilarClausesResponse> =>
    apiClient
      .get(`/projects/${projectId}/findings/${flagId}/similar`)
      .then((r) => r.data),
}

export interface SimilarClause {
  clause_id: string
  chunk_text: string
  score: number
}

export interface SimilarClausesResponse {
  finding_id: string
  count: number
  results: SimilarClause[]
}
