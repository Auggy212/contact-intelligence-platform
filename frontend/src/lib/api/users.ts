import { apiClient } from "./client"
import type { User, Membership, InviteMemberRequest, UpdateMemberRoleRequest } from "@/lib/types/api"

export const usersApi = {
  getMe: (): Promise<User> =>
    apiClient.get("/users/me").then((r) => r.data),

  listMembers: (): Promise<Membership[]> =>
    apiClient.get("/users").then((r) => r.data),

  invite: (data: InviteMemberRequest): Promise<Membership> =>
    apiClient.post("/users/invite", data).then((r) => r.data),

  updateRole: (membershipId: string, data: UpdateMemberRoleRequest): Promise<Membership> =>
    apiClient.patch(`/users/${membershipId}/role`, data).then((r) => r.data),

  remove: (membershipId: string): Promise<void> =>
    apiClient.delete(`/users/${membershipId}`).then(() => undefined),
}
