import { apiClient } from "./client"
import type { Project, ProjectCreate, ProjectUpdate } from "@/lib/types/api"

export const projectsApi = {
  list: (skip = 0, limit = 50): Promise<Project[]> =>
    apiClient.get("/projects", { params: { skip, limit } }).then((r) => r.data),

  get: (id: string): Promise<Project> =>
    apiClient.get(`/projects/${id}`).then((r) => r.data),

  create: (data: ProjectCreate): Promise<Project> =>
    apiClient.post("/projects", data).then((r) => r.data),

  update: (id: string, data: ProjectUpdate): Promise<Project> =>
    apiClient.patch(`/projects/${id}`, data).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/projects/${id}`).then(() => undefined),
}
