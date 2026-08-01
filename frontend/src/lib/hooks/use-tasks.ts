import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { tasksApi } from "@/lib/api/tasks"
import type { TaskTriggerRequest, ReviewFlagRequest, FlagType, Severity } from "@/lib/types/api"
import { dedupeFindings } from "@/lib/findings-dedup"
import { toast } from "sonner"

export const taskKeys = {
  detail: (id: string) => ["tasks", id] as const,
  projectTasks: (projectId: string) => ["project-tasks", projectId] as const,
  clause: (projectId: string, clauseId: string) => ["clause", projectId, clauseId] as const,
  findings: (projectId: string, filters?: object) => ["findings", projectId, filters] as const,
  modifications: (projectId: string) => ["modifications", projectId] as const,
}

export function useModifications(projectId: string) {
  return useQuery({
    queryKey: taskKeys.modifications(projectId),
    queryFn: () => tasksApi.getModifications(projectId),
    enabled: !!projectId,
  })
}

export function useTaskPolling(taskId: string, enabled: boolean) {
  return useQuery({
    queryKey: taskKeys.detail(taskId),
    queryFn: () => tasksApi.getTask(taskId),
    enabled: enabled && !!taskId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === "completed" || status === "failed") return false
      return 3000
    },
  })
}

export function useProjectTasks(projectId: string) {
  return useQuery({
    queryKey: taskKeys.projectTasks(projectId),
    queryFn: () => tasksApi.listProjectTasks(projectId),
    enabled: !!projectId,
  })
}

export function useClause(projectId: string, clauseId: string | null) {
  return useQuery({
    queryKey: taskKeys.clause(projectId, clauseId ?? ""),
    queryFn: () => tasksApi.getClause(projectId, clauseId!),
    enabled: !!projectId && !!clauseId,
  })
}

export function useTriggerTasks(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TaskTriggerRequest) => tasksApi.trigger(projectId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taskKeys.findings(projectId) })
      qc.invalidateQueries({ queryKey: taskKeys.projectTasks(projectId) })
      toast.success("Analysis started", { description: "Results will appear as tasks complete." })
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error("Failed to start analysis", { description: msg ?? "Check that all documents are uploaded." })
    },
  })
}

export function useFindings(projectId: string, filters?: { flag_type?: FlagType; severity?: Severity; reviewer_status?: string }) {
  return useQuery({
    queryKey: taskKeys.findings(projectId, filters),
    queryFn: () => tasksApi.getFindings(projectId, filters),
    enabled: !!projectId,
  })
}

/**
 * The count of DISTINCT issues for a project — i.e. raw findings after the same
 * de-duplication the Findings tab applies. Every tab that shows a "findings
 * count" (Overview, Analysis, Export) uses this so the numbers agree everywhere
 * instead of some tabs showing the raw flag count and others the deduped count.
 * Returns both so callers can show "89 issues (from 146 flags)" if useful.
 */
export function useIssueCount(projectId: string) {
  const { data: findings, isLoading } = useFindings(projectId)
  const raw = findings?.length ?? 0
  const issues = findings ? dedupeFindings(findings).length : 0
  return { issues, raw, isLoading }
}

export function useReviewFinding(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ flagId, data }: { flagId: string; data: ReviewFlagRequest }) =>
      tasksApi.reviewFinding(flagId, data),
    onSuccess: (_, { data }) => {
      qc.invalidateQueries({ queryKey: taskKeys.findings(projectId) })
      toast.success(data.status === "approved" ? "Finding approved" : "Finding rejected")
    },
  })
}
