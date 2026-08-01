import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { documentsApi } from "@/lib/api/documents"
import type { FileRole } from "@/lib/types/api"
import { toast } from "sonner"

export const docKeys = {
  list: (projectId: string) => ["documents", projectId] as const,
  content: (projectId: string, fileId: string) => ["doc-content", projectId, fileId] as const,
  clauses: (projectId: string, fileId: string) => ["doc-clauses", projectId, fileId] as const,
}

// Fetch the original file bytes for in-browser rendering (Verify view)
export function useDocumentContent(projectId: string, fileId: string | null) {
  return useQuery({
    queryKey: docKeys.content(projectId, fileId ?? ""),
    queryFn: () => documentsApi.getContent(projectId, fileId!),
    enabled: !!projectId && !!fileId,
    staleTime: 5 * 60 * 1000,
  })
}

// Fetch all parsed clauses for one file (Verify view clause-to-finding mapping)
export function useFileClauses(projectId: string, fileId: string | null) {
  return useQuery({
    queryKey: docKeys.clauses(projectId, fileId ?? ""),
    queryFn: () => documentsApi.listClauses(projectId, fileId!),
    enabled: !!projectId && !!fileId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useDocuments(projectId: string) {
  return useQuery({
    queryKey: docKeys.list(projectId),
    queryFn: () => documentsApi.list(projectId),
    enabled: !!projectId,
    staleTime: 0,           // always re-fetch when component mounts
    refetchOnMount: true,
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
