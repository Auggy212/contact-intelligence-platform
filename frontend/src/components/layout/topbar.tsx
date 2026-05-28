"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AlertTriangle, Building2, LogOut, ChevronDown } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { useSubscription } from "@/lib/hooks/use-billing"
import { getSession, clearSession, type MockUser } from "@/lib/auth"

const planBadgeClass: Record<string, string> = {
  trial: "bg-slate-100 text-slate-700 border-slate-300",
  starter: "bg-blue-100 text-blue-700 border-blue-300",
  professional: "bg-purple-100 text-purple-700 border-purple-300",
  enterprise: "bg-amber-100 text-amber-700 border-amber-300",
}

export function Topbar() {
  const router = useRouter()
  const { data: subscription } = useSubscription()
  const [user, setUser] = useState<MockUser | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    setUser(getSession())
  }, [])

  function handleLogout() {
    clearSession()
    router.replace("/")
  }

  return (
    <div className="flex flex-col">
      {subscription?.status === "past_due" && (
        <div className="bg-red-600 px-4 py-2 text-white text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>Payment failed. Your account may be suspended.</span>
          <Link href="/billing" className="underline font-medium ml-auto shrink-0">
            Update payment →
          </Link>
        </div>
      )}

      <header className="h-14 border-b bg-white flex items-center justify-between px-6 gap-4">
        {/* Org name */}
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <Building2 className="w-4 h-4 text-slate-400" />
          <span>ContractIQ</span>
        </div>

        <div className="flex items-center gap-3">
          {/* Plan badge */}
          {subscription && (
            <Badge
              variant="outline"
              className={cn("text-xs capitalize", planBadgeClass[subscription.plan] ?? "")}
            >
              {subscription.plan}
            </Badge>
          )}

          {/* User menu */}
          {user && (
            <div className="relative">
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-full pl-1 pr-3 py-1 transition-colors"
              >
                {/* Avatar circle */}
                <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
                  {user.initials}
                </div>
                <span className="font-medium max-w-[140px] truncate">{user.name}</span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              </button>

              {menuOpen && (
                <>
                  {/* Click-away overlay */}
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setMenuOpen(false)}
                  />
                  {/* Dropdown */}
                  <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-xl border border-slate-200 shadow-lg z-20 py-1 overflow-hidden">
                    <div className="px-4 py-3 border-b border-slate-100">
                      <p className="text-sm font-semibold text-slate-900 truncate">{user.name}</p>
                      <p className="text-xs text-slate-500 truncate">{user.email}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      Sign out
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </header>
    </div>
  )
}
