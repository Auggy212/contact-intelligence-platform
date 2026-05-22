"use client"

import Link from "next/link"
import { useParams, usePathname } from "next/navigation"
import { useProject } from "@/lib/hooks/use-projects"
import { ChevronRight, FolderOpen, Upload, BarChart2, Flag, Download } from "lucide-react"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"

const tabs = [
  { label: "Overview", href: "", icon: FolderOpen },
  { label: "Upload", href: "/upload", icon: Upload },
  { label: "Analysis", href: "/analysis", icon: BarChart2 },
  { label: "Findings", href: "/findings", icon: Flag },
  { label: "Export", href: "/export", icon: Download },
]

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const { projectId } = useParams<{ projectId: string }>()
  const pathname = usePathname()
  const { data: project, isLoading } = useProject(projectId)

  const base = `/projects/${projectId}`

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-sm text-slate-500 mb-4">
        <Link href="/projects" className="hover:text-slate-900 transition-colors">Projects</Link>
        <ChevronRight className="w-3.5 h-3.5" />
        {isLoading ? (
          <Skeleton className="h-4 w-32" />
        ) : (
          <span className="text-slate-900 font-medium truncate max-w-xs">{project?.name}</span>
        )}
      </div>

      {/* Project name */}
      {!isLoading && project && (
        <h1 className="text-xl font-bold text-slate-900 mb-5">{project.name}</h1>
      )}

      {/* Tab nav */}
      <div className="flex gap-1 border-b mb-6 -mx-0">
        {tabs.map((tab) => {
          const href = base + tab.href
          const isActive = tab.href === ""
            ? pathname === base
            : pathname.startsWith(href)
          return (
            <Link
              key={tab.href}
              href={href}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors",
                isActive
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300"
              )}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </Link>
          )
        })}
      </div>

      {children}
    </div>
  )
}
