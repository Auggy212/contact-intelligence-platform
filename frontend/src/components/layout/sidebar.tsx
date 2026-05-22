"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  FolderOpen, BookOpen, CheckSquare, Users, Shield,
  CreditCard, Settings, FileText,
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
    <aside className="flex flex-col h-full w-60 bg-slate-900 border-r border-slate-800">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-slate-800">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-600 shrink-0">
          <FileText className="w-4 h-4 text-white" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-white truncate">Contract Intel</p>
          <p className="text-xs text-slate-400 truncate">AI Legal Review</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                active
                  ? "bg-blue-600 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {item.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
