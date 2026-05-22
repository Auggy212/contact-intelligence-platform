import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { libraryApi } from "@/lib/api/library"
import type { ClauseLibraryCreate, ClauseLibraryUpdate } from "@/lib/types/api"
import { toast } from "sonner"

export const libraryKeys = {
  all: ["library"] as const,
  suggest: (q: string) => ["library", "suggest", q] as const,
}

export function useLibrary() {
  return useQuery({ queryKey: libraryKeys.all, queryFn: () => libraryApi.list() })
}

export function useLibrarySuggest(query: string) {
  return useQuery({
    queryKey: libraryKeys.suggest(query),
    queryFn: () => libraryApi.suggest(query),
    enabled: query.length >= 10,
    staleTime: 60_000,
  })
}

export function useCreateClause() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ClauseLibraryCreate) => libraryApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: libraryKeys.all }); toast.success("Clause added to library") },
  })
}

export function useUpdateClause() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ClauseLibraryUpdate }) => libraryApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: libraryKeys.all }); toast.success("Clause updated") },
  })
}

export function useDeleteClause() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => libraryApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: libraryKeys.all }); toast.success("Clause removed") },
  })
}
