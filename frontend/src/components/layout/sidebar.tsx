"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  FolderOpen, BookOpen, CheckSquare, Users, Shield,
  CreditCard, Settings, Scale, Eye,
} from "lucide-react"
import { cn } from "@/lib/utils"

type NavItem = { label: string; href: string; icon: typeof FolderOpen }

const navGroups: { heading: string; items: NavItem[] }[] = [
  {
    heading: "Workspace",
    items: [
      { label: "Projects", href: "/projects", icon: FolderOpen },
      { label: "Clause Library", href: "/library", icon: BookOpen },
      { label: "Checklist Rules", href: "/checklist", icon: CheckSquare },
      { label: "What We Check", href: "/what-we-check", icon: Eye },
    ],
  },
  {
    heading: "Organization",
    items: [
      { label: "Team", href: "/team", icon: Users },
      { label: "Audit Log", href: "/audit", icon: Shield },
      { label: "Billing", href: "/billing", icon: CreditCard },
      { label: "Settings", href: "/settings", icon: Settings },
    ],
  },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside
      className="relative flex h-full w-[248px] flex-col text-[hsl(38_20%_82%)]"
      style={{
        // Deep ink slab a touch darker than the canvas, with a faint amber
        // warmth bleeding up from the base — belongs to "The Lens" ground.
        backgroundImage:
          "linear-gradient(180deg, hsl(240 16% 9%) 0%, hsl(240 18% 7%) 60%, hsl(240 20% 5%) 100%)",
      }}
    >
      {/* Hairline separating sidebar from the ivory canvas + inner top highlight */}
      <div className="pointer-events-none absolute inset-y-0 right-0 w-px bg-white/5" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-white/8" />

      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-[1.35rem]">
        <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[hsl(42_100%_62%)] to-[hsl(32_96%_48%)] shadow-[0_4px_18px_-3px_hsl(38_96%_56%/0.65),inset_0_1px_1px_hsl(0_0%_100%/0.3)]">
          <Scale className="h-5 w-5 text-[hsl(40_60%_10%)]" strokeWidth={2.5} />
        </div>
        <div className="min-w-0">
          <p className="truncate text-[1rem] font-semibold tracking-[-0.02em] text-white">ContractIQ</p>
          <p className="truncate text-[0.7rem] font-medium text-[hsl(38_14%_58%)]">AI Legal Review</p>
        </div>
      </div>

      <div className="mx-5 h-px bg-white/6" />

      {/* Nav */}
      <nav className="flex-1 space-y-7 overflow-y-auto px-3.5 py-6">
        {navGroups.map((group) => (
          <div key={group.heading} className="space-y-1">
            <p className="px-3 pb-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-[hsl(38_12%_50%)]">
              {group.heading}
            </p>
            {group.items.map((item) => {
              const Icon = item.icon
              const active = pathname.startsWith(item.href)
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
                    active
                      ? "bg-white/[0.08] text-white shadow-[inset_0_1px_1px_hsl(0_0%_100%/0.06)]"
                      : "text-[hsl(38_16%_72%)] hover:bg-white/[0.04] hover:text-white",
                  )}
                >
                  {/* Active indicator bar */}
                  <span
                    className={cn(
                      "absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-full bg-gradient-to-b from-[hsl(42_100%_64%)] to-[hsl(32_96%_50%)] shadow-[0_0_12px_hsl(38_96%_56%/0.6)] transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]",
                      active ? "opacity-100" : "opacity-0 group-hover:opacity-30",
                    )}
                  />
                  <Icon
                    className={cn(
                      "h-[18px] w-[18px] shrink-0 transition-colors",
                      active ? "text-[hsl(42_100%_64%)]" : "text-[hsl(240_8%_52%)] group-hover:text-[hsl(44_16%_80%)]",
                    )}
                    strokeWidth={1.75}
                  />
                  {item.label}
                </Link>
              )
            })}
          </div>
        ))}
      </nav>

      {/* Footer badge */}
      <div className="px-4 py-4">
        <div className="flex items-center gap-2.5 rounded-xl border border-white/[0.06] bg-white/[0.03] px-3.5 py-3">
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
          </span>
          <p className="text-[0.7rem] leading-tight text-[hsl(38_14%_60%)]">
            <span className="font-medium text-[hsl(38_18%_82%)]">Deterministic engine</span><br />
            Offline · auditable · no LLM
          </p>
        </div>
      </div>
    </aside>
  )
}
