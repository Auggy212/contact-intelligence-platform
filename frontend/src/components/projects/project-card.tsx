"use client"

import Link from "next/link"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ProjectStatusBadge } from "./project-status-badge"
import { formatRelative } from "@/lib/utils"
import type { Project } from "@/lib/types/api"
import { FolderOpen, ArrowRight } from "lucide-react"

export function ProjectCard({ project }: { project: Project }) {
  return (
    <Link href={`/projects/${project.id}`}>
      <Card className="hover:shadow-md hover:border-blue-200 transition-all cursor-pointer h-full group">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                <FolderOpen className="w-4 h-4 text-blue-600" />
              </div>
              <h3 className="font-semibold text-slate-900 text-sm leading-tight line-clamp-2">
                {project.name}
              </h3>
            </div>
            <ProjectStatusBadge status={project.status} />
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {project.description && (
            <p className="text-xs text-slate-500 line-clamp-2 mb-3">
              {project.description}
            </p>
          )}
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">{formatRelative(project.created_at)}</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-blue-500 transition-colors" />
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
