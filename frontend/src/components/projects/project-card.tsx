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
      <Card className="group relative h-full transition-all duration-200 ease-out-quint hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-lg">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <Link href={`/projects/${project.id}`} className="flex min-w-0 flex-1 items-center gap-2.5">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/8 text-primary transition-colors group-hover:bg-primary/12">
                <FolderOpen className="h-[18px] w-[18px]" strokeWidth={2} />
              </div>
              <h3 className="line-clamp-2 text-sm font-semibold leading-tight tracking-[-0.01em] text-foreground">
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
                    className="cursor-pointer text-destructive focus:bg-destructive/8 focus:text-destructive"
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
              <p className="mb-3 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                {project.description}
              </p>
            )}
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground/80">{formatRelative(project.created_at)}</span>
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
