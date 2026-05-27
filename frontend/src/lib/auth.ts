/**
 * Mock authentication — no Clerk, no external keys required.
 * Session is stored in localStorage (user data) and a "cip_session=1" cookie
 * (so the middleware can protect dashboard routes server-side).
 */

export interface MockUser {
  name: string
  email: string
  /** initials derived from name, used in avatar */
  initials: string
}

const STORAGE_KEY = "cip_user"
const SESSION_COOKIE = "cip_session"

function setCookie(value: string, days = 7) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString()
  document.cookie = `${SESSION_COOKIE}=${value}; expires=${expires}; path=/; SameSite=Lax`
}

function clearCookie() {
  document.cookie = `${SESSION_COOKIE}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; SameSite=Lax`
}

export function getSession(): MockUser | null {
  if (typeof window === "undefined") return null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as MockUser
  } catch {
    return null
  }
}

export function saveSession(name: string, email: string): MockUser {
  const parts = name.trim().split(/\s+/)
  const initials =
    parts.length >= 2
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : name.slice(0, 2).toUpperCase()
  const user: MockUser = { name: name.trim(), email: email.trim(), initials }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
  setCookie("1")
  return user
}

export function clearSession(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(STORAGE_KEY)
  clearCookie()
}

export function isAuthenticated(): boolean {
  return getSession() !== null
}
