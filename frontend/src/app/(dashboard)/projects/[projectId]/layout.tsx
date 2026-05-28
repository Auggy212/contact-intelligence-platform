"use client"

import { useState } from "react"
import Link from "next/link"
import { useParams, usePathname, useRouter } from "next/navigation"
import { useProject } from "@/lib/hooks/use-projects"
import { EditProjectDialog } from "@/components/projects/edit-project-dialog"
import { DeleteProjectDialog } from "@/components/projects/delete-project-dialog"
import { Button } from "@/components/ui/button"
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
      <div className="flex items-center gap-1.5 text-sm text-slate-500 mb-4">
        <Link href="/projects" className="hover:text-slate-900 transition-colors">Projects</Link>
        <ChevronRight className="w-3.5 h-3.5" />
        {isLoading ? (
          <Skeleton className="h-4 w-32" />
        ) : (
          <span className="text-slate-900 font-medium truncate max-w-xs">{project?.name}</span>
        )}
      </div>

      {/* Project name + actions */}
      {!isLoading && project && (
        <div className="flex items-center justify-between mb-5 gap-3">
          <h1 className="text-xl font-bold text-slate-900 truncate">{project.name}</h1>
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setEditOpen(true)}
              className="gap-1.5"
            >
              <Pencil className="w-3.5 h-3.5" />
              Edit
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeleteOpen(true)}
              className="gap-1.5 text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700 hover:border-red-300"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete
            </Button>
          </div>
        </div>
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

      <EditProjectDialog
        project={project ?? null}
        open={editOpen}
        onOpenChange={setEditOpen}
      />

      <DeleteProjectDialog
        project={project ?? null}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onDeleted={() => router.push("/projects")}
      />
    </div>
  )
}
