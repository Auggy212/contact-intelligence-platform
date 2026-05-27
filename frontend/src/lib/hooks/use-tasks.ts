import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { tasksApi } from "@/lib/api/tasks"
import type { TaskTriggerRequest, ReviewFlagRequest, FlagType, Severity } from "@/lib/types/api"
import { toast } from "sonner"

export const taskKeys = {
  detail: (id: string) => ["tasks", id] as const,
  findings: (projectId: string, filters?: object) => ["findings", projectId, filters] as const,
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

export function useTriggerTasks(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TaskTriggerRequest) => tasksApi.trigger(projectId, data),
    onSuccess: () => {
      // Invalidate findings cache so the findings page always shows fresh results
      qc.invalidateQueries({ queryKey: taskKeys.findings(projectId) })
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
