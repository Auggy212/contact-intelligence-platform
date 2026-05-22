import axios from "axios"
import { toast } from "sonner"

type TokenGetter = () => Promise<string | null>

let _getToken: TokenGetter | null = null

export function setAuthTokenGetter(fn: TokenGetter) {
  _getToken = fn
}

export const apiClient = axios.create({
  baseURL: `${process.env.NEXT_PUBLIC_API_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
})

apiClient.interceptors.request.use(async (config) => {
  if (_getToken) {
    try {
      const token = await _getToken()
      if (token) config.headers.Authorization = `Bearer ${token}`
    } catch {
      // token fetch failed — proceed without auth header
    }
  }
  return config
})

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error?.response?.status
    if (status === 402) {
      toast.error("Plan limit reached", {
        description: "Upgrade your plan to continue.",
        action: { label: "Upgrade", onClick: () => { window.location.href = "/billing" } },
      })
    } else if (status === 403) {
      toast.error("Permission denied", { description: "You don't have permission for this action." })
    } else if (status === 500) {
      toast.error("Server error", { description: "Please try again in a moment." })
    }

    return Promise.reject(error)
  }
)
