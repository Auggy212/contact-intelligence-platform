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
  trial: "bg-secondary text-secondary-foreground border-border",
  starter: "bg-sev-low-bg text-sev-low border-sev-low-border",
  professional: "bg-sev-critical-bg text-sev-critical border-sev-critical-border",
  enterprise: "bg-sev-medium-bg text-sev-medium border-sev-medium-border",
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

      <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-border/70 bg-[hsl(240_18%_7%/0.72)] px-6 backdrop-blur-xl">
        {/* Org name */}
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Building2 className="h-4 w-4 text-muted-foreground/70" />
          <span className="font-semibold tracking-[-0.01em] text-foreground">ContractIQ</span>
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
                className="flex items-center gap-2 rounded-full py-1 pl-1 pr-3 text-sm text-muted-foreground transition-colors duration-150 ease-out-quint hover:bg-secondary hover:text-foreground"
              >
                {/* Avatar circle */}
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[hsl(42_100%_60%)] to-[hsl(32_96%_48%)] text-xs font-bold text-[hsl(40_60%_10%)] shadow-sm">
                  {user.initials}
                </div>
                <span className="max-w-[140px] truncate font-medium">{user.name}</span>
                <ChevronDown className={cn("h-3.5 w-3.5 shrink-0 text-muted-foreground/70 transition-transform duration-200 ease-out-quint", menuOpen && "rotate-180")} />
              </button>

              {menuOpen && (
                <>
                  {/* Click-away overlay */}
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setMenuOpen(false)}
                  />
                  {/* Dropdown — solid opaque surface, own stacking context above the
                      blurred header so it never renders translucent. */}
                  <div
                    className="animate-fade-in absolute right-0 top-full z-50 mt-2 w-60 origin-top-right overflow-hidden rounded-xl border border-border py-1 shadow-lg"
                    style={{ backgroundColor: "hsl(240 17% 11%)" }}
                  >
                    <div className="border-b border-border/70 px-4 py-3">
                      <p className="truncate text-sm font-semibold text-foreground">{user.name}</p>
                      <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
                    >
                      <LogOut className="h-4 w-4" />
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
