import { apiClient } from "./client"

export interface ConceptItem {
  name: string
  severity: string
  risk_score: number | null
  recommendation: string
}
export interface ConceptsResponse {
  total: number
  concepts: ConceptItem[]
}

export interface LawCheck {
  id: string
  title: string
  act_name: string
  section: string
  severity: string
  law_text: string
  recommendation: string
  jurisdiction: string
}
export interface LawAct {
  act_name: string
  count: number
  checks: LawCheck[]
}
export interface LawCorpusResponse {
  total_checks: number
  total_acts: number
  acts: LawAct[]
}

export const transparencyApi = {
  concepts: (): Promise<ConceptsResponse> =>
    apiClient.get("/transparency/concepts").then((r) => r.data),

  lawCorpus: (): Promise<LawCorpusResponse> =>
    apiClient.get("/transparency/law-corpus").then((r) => r.data),
}
