import { useQuery } from "@tanstack/react-query"
import { transparencyApi } from "@/lib/api/transparency"

export function useConcepts() {
  return useQuery({
    queryKey: ["transparency", "concepts"],
    queryFn: transparencyApi.concepts,
    staleTime: 1000 * 60 * 60, // engine definitions rarely change within a session
  })
}

export function useLawCorpus() {
  return useQuery({
    queryKey: ["transparency", "law-corpus"],
    queryFn: transparencyApi.lawCorpus,
    staleTime: 1000 * 60 * 60,
  })
}
