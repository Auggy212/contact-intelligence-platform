import { apiClient } from "./client"
import type { ProjectFile, DocumentUploadResponse, FileRole } from "@/lib/types/api"

export interface FileClause {
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

export const documentsApi = {
  list: (projectId: string): Promise<ProjectFile[]> =>
    apiClient.get(`/projects/${projectId}/documents`).then((r) => r.data),

  // Stream the original uploaded file bytes (untouched) for in-browser preview
  getContent: (projectId: string, fileId: string): Promise<ArrayBuffer> =>
    apiClient
      .get(`/projects/${projectId}/documents/${fileId}/content`, {
        responseType: "arraybuffer",
      })
      .then((r) => r.data),

  // All parsed clauses for one file, ordered by document position
  listClauses: (projectId: string, fileId: string): Promise<FileClause[]> =>
    apiClient.get(`/projects/${projectId}/documents/${fileId}/clauses`).then((r) => r.data),

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

  delete: (projectId: string, fileId: string): Promise<void> =>
    apiClient.delete(`/projects/${projectId}/documents/${fileId}`).then(() => undefined),
}
