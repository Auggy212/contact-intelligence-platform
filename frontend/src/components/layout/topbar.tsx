"use client"

import { useSubscription } from "@/lib/hooks/use-billing"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, Bell, Building2, Search, User } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"

const planBadgeClass: Record<string, string> = {
  trial:        "bg-zinc-800 text-zinc-300 border-zinc-700",
  starter:      "bg-orange-500/15 text-orange-400 border-orange-500/25",
  professional: "bg-amber-500/15 text-amber-400 border-amber-500/25",
  enterprise:   "bg-yellow-500/15 text-yellow-400 border-yellow-500/25",
}

export function Topbar() {
  const { data: subscription } = useSubscription()

  return (
    <div className="flex flex-col">
      {/* Past-due banner */}
      {subscription?.status === "past_due" && (
        <div className="flex items-center gap-2 bg-red-600/90 px-4 py-2 text-sm text-white animate-fade-in">
          <AlertTriangle className="h-4 w-4 shrink-0 animate-pulse" />
          <span>Payment failed — your account may be suspended.</span>
          <Link href="/billing" className="ml-auto shrink-0 font-semibold underline hover:no-underline">
            Update payment →
          </Link>
        </div>
      )}

      <header className="flex h-14 items-center justify-between border-b border-white/[0.06] bg-background px-5 gap-4 animate-fade-in">
        {/* Org name */}
        <div className="flex items-center gap-2 text-sm font-medium text-zinc-400 transition-all hover:text-zinc-200 cursor-default animate-fade-in delay-75">
          <Building2 className="h-4 w-4 text-zinc-600" />
          <span>Dev Organisation</span>
        </div>

        {/* Search bar */}
        <div className="relative hidden max-w-xs flex-1 sm:block animate-fade-in delay-100">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-600 transition-colors duration-200 group-focus-within:text-orange-500" />
          <input
            type="search"
            placeholder="Search projects, clauses…"
            className="h-8 w-full rounded-lg border border-white/[0.06] bg-white/[0.04] pl-9 pr-4 text-xs text-zinc-300 placeholder-zinc-700 outline-none transition-all duration-300 focus:border-orange-500/40 focus:bg-white/[0.06] focus:ring-2 focus:ring-orange-500/10"
          />
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3 animate-fade-in delay-150">
          {subscription && (
            <Badge variant="outline"
              className={cn("text-xs capitalize border cursor-default select-none transition-transform hover:scale-105 duration-200", planBadgeClass[subscription.plan] ?? "bg-zinc-800 text-zinc-400 border-zinc-700")}>
              {subscription.plan}
            </Badge>
          )}

          {/* Notification bell */}
          <button className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.06] bg-white/[0.03] text-zinc-500 hover:border-white/[0.1] hover:text-zinc-300 active:scale-95 transition-all hover:scale-105 duration-200">
            <Bell className="h-3.5 w-3.5" />
          </button>

          {/* User avatar */}
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-500/15 text-xs font-bold text-orange-400 cursor-pointer select-none transition-all hover:scale-110 active:scale-95 hover:glow-orange-sm duration-200">
            D
          </div>
        </div>
      </header>
    </div>
  )
}
