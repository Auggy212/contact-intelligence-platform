"use client"

// DEV BYPASS MODE
// The backend runs with APP_ENV=testing, which accepts X-Test-Tenant-Id and
// X-Test-User-Id headers instead of a real Clerk JWT.
// To restore Clerk auth: replace this file and set APP_ENV=development in backend.

import { useEffect } from "react"
import { apiClient } from "@/lib/api/client"

const DEV_TENANT_ID = "00000000-0000-0000-0000-000000000001"
const DEV_USER_ID = "00000000-0000-0000-0000-000000000002"

export function AuthSync() {
  useEffect(() => {
    const interceptor = apiClient.interceptors.request.use((config) => {
      config.headers["X-Test-Tenant-Id"] = DEV_TENANT_ID
      config.headers["X-Test-User-Id"] = DEV_USER_ID
      return config
    })
    return () => apiClient.interceptors.request.eject(interceptor)
  }, [])

  return null
}
