import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { documentsApi } from "@/lib/api/documents"
import type { FileRole } from "@/lib/types/api"
import { toast } from "sonner"

export const docKeys = {
  list: (projectId: string) => ["documents", projectId] as const,
}

export function useDocuments(projectId: string) {
  return useQuery({
    queryKey: docKeys.list(projectId),
    queryFn: () => documentsApi.list(projectId),
    enabled: !!projectId,
    refetchInterval: (query) => {
      const docs = query.state.data
      if (!docs) return false
      const hasPending = docs.some((d) => d.parse_status === "pending" || d.parse_status === "processing")
      return hasPending ? 3000 : false
    },
  })
}

export function useUploadDocument(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      fileRole,
      file,
      onProgress,
    }: {
      fileRole: FileRole
      file: File
      onProgress?: (pct: number) => void
    }) => documentsApi.upload(projectId, fileRole, file, onProgress),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: docKeys.list(projectId) })
      toast.success("Document uploaded")
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error("Upload failed", { description: msg ?? "Check the file type and try again." })
    },
  })
}

export function useDeleteDocument(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (fileId: string) => documentsApi.delete(projectId, fileId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: docKeys.list(projectId) })
      toast.success("Document removed")
    },
    onError: () => {
      toast.error("Failed to remove document")
    },
  })
}
