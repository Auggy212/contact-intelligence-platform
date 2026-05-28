"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ProjectStatusBadge } from "./project-status-badge"
import { EditProjectDialog } from "./edit-project-dialog"
import { DeleteProjectDialog } from "./delete-project-dialog"
import { formatRelative } from "@/lib/utils"
import type { Project } from "@/lib/types/api"
import { FolderOpen, MoreVertical, Pencil, Trash2 } from "lucide-react"

export function ProjectCard({ project }: { project: Project }) {
  const router = useRouter()
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  return (
    <>
      <Card className="hover:shadow-md hover:border-blue-200 transition-all h-full group relative">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <Link href={`/projects/${project.id}`} className="flex items-center gap-2 min-w-0 flex-1">
              <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                <FolderOpen className="w-4 h-4 text-blue-600" />
              </div>
              <h3 className="font-semibold text-slate-900 text-sm leading-tight line-clamp-2">
                {project.name}
              </h3>
            </Link>
            <div className="flex items-center gap-1.5 shrink-0">
              <ProjectStatusBadge status={project.status} />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => e.preventDefault()}
                  >
                    <MoreVertical className="w-4 h-4 text-slate-500" />
                    <span className="sr-only">Project actions</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-40">
                  <DropdownMenuItem
                    onClick={(e) => { e.preventDefault(); setEditOpen(true) }}
                    className="cursor-pointer"
                  >
                    <Pencil className="w-3.5 h-3.5 mr-2" />
                    Edit
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={(e) => { e.preventDefault(); setDeleteOpen(true) }}
                    className="cursor-pointer text-red-600 focus:text-red-600 focus:bg-red-50"
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-2" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <Link href={`/projects/${project.id}`} className="block">
            {project.description && (
              <p className="text-xs text-slate-500 line-clamp-2 mb-3">
                {project.description}
              </p>
            )}
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">{formatRelative(project.created_at)}</span>
            </div>
          </Link>
        </CardContent>
      </Card>

      <EditProjectDialog
        project={project}
        open={editOpen}
        onOpenChange={setEditOpen}
      />

      <DeleteProjectDialog
        project={project}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onDeleted={() => router.push("/projects")}
      />
    </>
  )
}
