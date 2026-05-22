import { apiClient } from "./client"
import type { Organization, OrganizationUpdate, Workspace, WorkspaceCreate, WorkspaceUpdate } from "@/lib/types/api"

export const organizationsApi = {
  getMe: (): Promise<Organization> =>
    apiClient.get("/organizations/me").then((r) => r.data),

  update: (data: OrganizationUpdate): Promise<Organization> =>
    apiClient.patch("/organizations/me", data).then((r) => r.data),

  getWorkspaces: (): Promise<Workspace[]> =>
    apiClient.get("/organizations/me/workspaces").then((r) => r.data),

  createWorkspace: (data: WorkspaceCreate): Promise<Workspace> =>
    apiClient.post("/organizations/me/workspaces", data).then((r) => r.data),

  updateWorkspace: (id: string, data: WorkspaceUpdate): Promise<Workspace> =>
    apiClient.patch(`/organizations/me/workspaces/${id}`, data).then((r) => r.data),
}
