"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  FolderOpen, BookOpen, CheckSquare, Users, Shield,
  CreditCard, Settings, FileText, ChevronRight,
} from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { label: "Projects", href: "/projects", icon: FolderOpen },
  { label: "Clause Library", href: "/library", icon: BookOpen },
  { label: "Checklist Rules", href: "/checklist", icon: CheckSquare },
  { label: "Team", href: "/team", icon: Users },
  { label: "Audit Log", href: "/audit", icon: Shield },
  { label: "Billing", href: "/billing", icon: CreditCard },
  { label: "Settings", href: "/settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex h-full flex-col border-r border-white/[0.06] bg-background animate-slide-left" style={{ width: "var(--sidebar-width, 240px)" }}>
      {/* Logo */}
      <div className="flex items-center gap-2.5 border-b border-white/[0.06] px-5 py-4 animate-fade-in delay-100">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-orange-500 transition-transform duration-300 hover:rotate-12">
          <FileText className="h-4 w-4 text-white" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-white">Contract Intel</p>
          <p className="truncate text-xs text-zinc-600">AI Legal Review</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {navItems.map((item, i) => {
          const Icon = item.icon
          const active = pathname.startsWith(item.href)
          return (
            <Link key={item.href} href={item.href}
              style={{ animationDelay: `${i * 45}ms` }}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all relative animate-fade-in",
                active
                  ? "bg-orange-500/12 text-orange-400 border border-orange-500/20"
                  : "text-zinc-500 hover:bg-white/[0.04] hover:text-zinc-200 border border-transparent"
              )}>
              {active && <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-orange-500 animate-pulse" />}
              <Icon className={cn("h-4 w-4 shrink-0 transition-transform group-hover:scale-110", active ? "text-orange-400" : "text-zinc-600 group-hover:text-zinc-400")} />
              <span className="flex-1 transition-transform group-hover:translate-x-0.5">{item.label}</span>
              {active && <ChevronRight className="h-3.5 w-3.5 text-orange-400/50" />}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-white/[0.06] p-4 animate-fade-in delay-300">
        <div className="flex items-center gap-3 rounded-lg bg-white/[0.03] px-3 py-2.5 transition-all hover:bg-white/[0.06] duration-300">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-orange-500/15 text-xs font-bold text-orange-400">
            D
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-semibold text-white">Dev Admin</p>
            <p className="truncate text-xs text-zinc-600">dev@contractintel.in</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
