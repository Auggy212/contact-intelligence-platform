"use client"

import { useSubscription } from "@/lib/hooks/use-billing"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, Building2, User } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"

const planBadgeClass: Record<string, string> = {
  trial: "bg-slate-100 text-slate-700 border-slate-300",
  starter: "bg-blue-100 text-blue-700 border-blue-300",
  professional: "bg-purple-100 text-purple-700 border-purple-300",
  enterprise: "bg-amber-100 text-amber-700 border-amber-300",
}

export function Topbar() {
  const { data: subscription } = useSubscription()

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
        {/* Org indicator */}
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <Building2 className="w-4 h-4 text-slate-400" />
          <span>Dev Organisation</span>
        </div>

        <div className="flex items-center gap-3">
          {subscription && (
            <Badge
              variant="outline"
              className={cn("text-xs capitalize", planBadgeClass[subscription.plan] ?? "")}
            >
              {subscription.plan}
            </Badge>
          )}
          {/* Dev user indicator */}
          <div className="flex items-center gap-2 text-sm text-slate-500 bg-slate-100 rounded-full px-3 py-1">
            <User className="w-3.5 h-3.5" />
            <span>Dev Admin</span>
          </div>
        </div>
      </header>
    </div>
  )
}
