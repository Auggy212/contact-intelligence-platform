"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ProjectStatusBadge } from "./project-status-badge"
import { EditProjectDialog } from "./edit-project-dialog"
import { DeleteProjectDialog } from "./delete-project-dialog"
import { formatRelative } from "@/lib/utils"
import type { Project } from "@/lib/types/api"
import { ArrowRight, FolderOpen, MoreVertical, Pencil, Trash2 } from "lucide-react"

export function ProjectCard({ project }: { project: Project }) {
  const router = useRouter()
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  return (
    <>
      <div className="group relative flex h-full flex-col rounded-xl border border-white/[0.07] bg-[#111111] p-5 transition-all hover:border-orange-500/30 hover:bg-[#14151A] hover:shadow-lg hover:shadow-orange-500/5">
        {/* Orange hover glow line */}
        <div className="absolute inset-x-0 top-0 h-px rounded-t-xl bg-gradient-to-r from-transparent via-orange-500/0 to-transparent transition-all group-hover:via-orange-500/40" />

        {/* Header */}
        <div className="mb-4 flex items-start justify-between gap-2">
          <Link href={`/projects/${project.id}`} className="flex items-center gap-3 min-w-0 flex-1">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-orange-500/10 ring-1 ring-orange-500/15 group-hover:bg-orange-500/20 transition-all">
              <FolderOpen className="h-4 w-4 text-orange-400" />
            </div>
            <h3 className="truncate text-sm font-bold text-white leading-snug line-clamp-2">
              {project.name}
            </h3>
          </Link>

          <div className="flex items-center gap-1.5 shrink-0">
            <ProjectStatusBadge status={project.status} />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  className="flex h-6 w-6 items-center justify-center rounded-md text-zinc-600 opacity-0 transition-all hover:bg-white/[0.06] hover:text-zinc-300 group-hover:opacity-100"
                  onClick={(e) => e.preventDefault()}
                >
                  <MoreVertical className="h-3.5 w-3.5" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-36 border-white/[0.08] bg-[#1C1E26]">
                <DropdownMenuItem
                  onClick={(e) => { e.preventDefault(); setEditOpen(true) }}
                  className="cursor-pointer text-zinc-300 focus:bg-white/[0.05] focus:text-white"
                >
                  <Pencil className="mr-2 h-3.5 w-3.5" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-white/[0.06]" />
                <DropdownMenuItem
                  onClick={(e) => { e.preventDefault(); setDeleteOpen(true) }}
                  className="cursor-pointer text-red-400 focus:bg-red-500/10 focus:text-red-400"
                >
                  <Trash2 className="mr-2 h-3.5 w-3.5" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Description */}
        <Link href={`/projects/${project.id}`} className="flex-1">
          {project.description && (
            <p className="mb-4 text-xs leading-relaxed text-zinc-600 line-clamp-2">
              {project.description}
            </p>
          )}
          {/* Footer */}
          <div className="flex items-center justify-between border-t border-white/[0.05] pt-3">
            <span className="text-xs text-zinc-600">{formatRelative(project.created_at)}</span>
            <ArrowRight className="h-3.5 w-3.5 text-zinc-700 transition-all group-hover:text-orange-400 group-hover:translate-x-0.5" />
          </div>
        </Link>
      </div>

      <EditProjectDialog project={project} open={editOpen} onOpenChange={setEditOpen} />
      <DeleteProjectDialog
        project={project}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onDeleted={() => router.push("/projects")}
      />
    </>
  )
}
