import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { organizationsApi } from "@/lib/api/organizations"
import type { OrganizationUpdate, WorkspaceCreate, WorkspaceUpdate } from "@/lib/types/api"
import { toast } from "sonner"

export function useOrganization() {
  const qc = useQueryClient()
  const query = useQuery({
    queryKey: ["organization"],
    queryFn: () => organizationsApi.getMe(),
  })
  const { mutate: update, isPending: updating } = useMutation({
    mutationFn: (data: OrganizationUpdate) => organizationsApi.update(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["organization"] })
      toast.success("Organisation updated")
    },
    onError: () => toast.error("Failed to save changes"),
  })
  return { ...query, update, updating }
}

export function useWorkspaces() {
  return useQuery({
    queryKey: ["workspaces"],
    queryFn: () => organizationsApi.getWorkspaces(),
  })
}

export function useCreateWorkspace() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WorkspaceCreate) => organizationsApi.createWorkspace(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workspaces"] })
      toast.success("Workspace created")
    },
    onError: () => toast.error("Failed to create workspace"),
  })
}

export function useUpdateWorkspace() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WorkspaceUpdate }) =>
      organizationsApi.updateWorkspace(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workspaces"] })
      toast.success("Workspace updated")
    },
    onError: () => toast.error("Failed to update workspace"),
  })
}
