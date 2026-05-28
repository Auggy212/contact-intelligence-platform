"use client"

import { useState } from "react"
import Link from "next/link"
import { useParams, usePathname, useRouter } from "next/navigation"
import { useProject } from "@/lib/hooks/use-projects"
import { EditProjectDialog } from "@/components/projects/edit-project-dialog"
import { DeleteProjectDialog } from "@/components/projects/delete-project-dialog"
import { ChevronRight, FolderOpen, Upload, BarChart2, Flag, Download, Pencil, Trash2 } from "lucide-react"
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
  const router = useRouter()
  const { data: project, isLoading } = useProject(projectId)
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const base = `/projects/${projectId}`

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-4 flex items-center gap-1.5 text-sm animate-fade-in">
        <Link href="/projects" className="text-zinc-500 transition-colors hover:text-zinc-200">
          Projects
        </Link>
        <ChevronRight className="h-3.5 w-3.5 text-zinc-700" />
        {isLoading ? (
          <Skeleton className="h-4 w-32" />
        ) : (
          <span className="max-w-xs truncate font-medium text-zinc-300">{project?.name}</span>
        )}
      </div>

      {/* Project name + actions */}
      {!isLoading && project && (
        <div className="mb-5 flex items-center justify-between gap-3 animate-fade-up">
          <h1 className="truncate text-xl font-bold text-white">{project.name}</h1>
          <div className="flex shrink-0 items-center gap-2">
            <button
              onClick={() => setEditOpen(true)}
              className="flex h-8 items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 text-xs font-medium text-zinc-400 transition-all hover:border-white/[0.14] hover:text-zinc-200"
            >
              <Pencil className="h-3.5 w-3.5" />
              Edit
            </button>
            <button
              onClick={() => setDeleteOpen(true)}
              className="flex h-8 items-center gap-1.5 rounded-lg border border-red-500/20 bg-red-500/5 px-3 text-xs font-medium text-red-400 transition-all hover:border-red-500/40 hover:bg-red-500/10"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete
            </button>
          </div>
        </div>
      )}

      {/* Tab nav */}
      <div className="mb-6 flex gap-1 border-b border-white/[0.06] animate-fade-in delay-75">
        {tabs.map((tab) => {
          const href = base + tab.href
          const isActive = tab.href === "" ? pathname === base : pathname.startsWith(href)
          return (
            <Link
              key={tab.href}
              href={href}
              className={cn(
                "flex items-center gap-2 border-b-2 -mb-px px-4 py-2.5 text-sm font-medium transition-all",
                isActive
                  ? "border-orange-500 text-orange-400"
                  : "border-transparent text-zinc-500 hover:border-zinc-700 hover:text-zinc-300"
              )}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </Link>
          )
        })}
      </div>

      {children}

      <EditProjectDialog project={project ?? null} open={editOpen} onOpenChange={setEditOpen} />
      <DeleteProjectDialog
        project={project ?? null}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onDeleted={() => router.push("/projects")}
      />
    </div>
  )
}
