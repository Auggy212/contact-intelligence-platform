import { apiClient } from "./client"
import type { ProjectFile, DocumentUploadResponse, FileRole } from "@/lib/types/api"

export const documentsApi = {
  list: (projectId: string): Promise<ProjectFile[]> =>
    apiClient.get(`/projects/${projectId}/documents`).then((r) => r.data),

  upload: (
    projectId: string,
    fileRole: FileRole,
    file: File,
    onProgress?: (pct: number) => void
  ): Promise<DocumentUploadResponse> => {
    const form = new FormData()
    form.append("file_role", fileRole)
    form.append("file", file)
    return apiClient
      .post(`/projects/${projectId}/documents`, form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total))
        },
      })
      .then((r) => r.data)
  },

  getDownloadUrl: (projectId: string, fileId: string): Promise<{ download_url: string }> =>
    apiClient.get(`/projects/${projectId}/documents/${fileId}/download-url`).then((r) => r.data),
}
