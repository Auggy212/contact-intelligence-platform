import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { checklistApi } from "@/lib/api/checklist"
import type { ChecklistRuleCreate, ChecklistRuleUpdate } from "@/lib/types/api"
import { toast } from "sonner"

export const checklistKeys = { all: ["checklist-rules"] as const }

export function useChecklist() {
  return useQuery({ queryKey: checklistKeys.all, queryFn: () => checklistApi.list() })
}

export function useCreateRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ChecklistRuleCreate) => checklistApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: checklistKeys.all }); toast.success("Rule created") },
  })
}

export function useUpdateRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ChecklistRuleUpdate }) => checklistApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: checklistKeys.all }); toast.success("Rule updated") },
  })
}

export function useDeleteRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => checklistApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: checklistKeys.all }); toast.success("Rule deleted") },
  })
}
