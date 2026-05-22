import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { usersApi } from "@/lib/api/users"
import type { InviteMemberRequest, UpdateMemberRoleRequest } from "@/lib/types/api"
import { toast } from "sonner"

export const teamKeys = { all: ["team"] as const }

export function useTeam() {
  return useQuery({ queryKey: teamKeys.all, queryFn: () => usersApi.listMembers() })
}

export function useInviteMember() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: InviteMemberRequest) => usersApi.invite(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: teamKeys.all }); toast.success("Invitation sent") },
  })
}

export function useUpdateMemberRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateMemberRoleRequest }) => usersApi.updateRole(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: teamKeys.all }); toast.success("Role updated") },
  })
}

export function useRemoveMember() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => usersApi.remove(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: teamKeys.all }); toast.success("Member removed") },
  })
}
