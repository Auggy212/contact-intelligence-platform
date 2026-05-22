import { apiClient } from "./client"

export const exportApi = {
  downloadPdf: async (projectId: string, projectName: string): Promise<void> => {
    const response = await apiClient.get(`/projects/${projectId}/export/pdf`, {
      responseType: "blob",
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement("a")
    link.href = url
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, "")
    const safeName = projectName.replace(/[^a-z0-9]/gi, "_").toLowerCase()
    link.setAttribute("download", `contract_review_${safeName}_${date}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.parentNode?.removeChild(link)
    window.URL.revokeObjectURL(url)
  },
}
