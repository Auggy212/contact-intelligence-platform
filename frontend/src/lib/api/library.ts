import { apiClient } from "./client"
import type { ClauseLibraryEntry, ClauseLibraryCreate, ClauseLibraryUpdate } from "@/lib/types/api"

export const libraryApi = {
  list: (): Promise<ClauseLibraryEntry[]> =>
    apiClient.get("/clause-library").then((r) => r.data),

  suggest: (query: string, topK = 5): Promise<ClauseLibraryEntry[]> =>
    apiClient.get("/clause-library/suggest", { params: { q: query, top_k: topK } }).then((r) => r.data),

  create: (data: ClauseLibraryCreate): Promise<ClauseLibraryEntry> =>
    apiClient.post("/clause-library", data).then((r) => r.data),

  update: (id: string, data: ClauseLibraryUpdate): Promise<ClauseLibraryEntry> =>
    apiClient.patch(`/clause-library/${id}`, data).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/clause-library/${id}`).then(() => undefined),
}
