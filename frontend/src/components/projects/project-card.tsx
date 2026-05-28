"use client"

import Link from "next/link"
import { ProjectStatusBadge } from "./project-status-badge"
import { formatRelative } from "@/lib/utils"
import type { Project } from "@/lib/types/api"
import { ArrowRight, FolderOpen } from "lucide-react"

export function ProjectCard({ project }: { project: Project }) {
  return (
    <Link href={`/projects/${project.id}`}>
      <div className="group relative flex h-full flex-col rounded-xl border border-white/[0.07] bg-[#111111] p-5 transition-all hover:border-orange-500/30 hover:bg-[#14151A] hover:shadow-lg hover:shadow-orange-500/5 cursor-pointer">
        {/* Orange hover glow line */}
        <div className="absolute inset-x-0 top-0 h-px rounded-t-xl bg-gradient-to-r from-transparent via-orange-500/0 to-transparent transition-all group-hover:via-orange-500/40" />

        {/* Header */}
        <div className="mb-4 flex items-start justify-between gap-2">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-orange-500/10 ring-1 ring-orange-500/15 group-hover:bg-orange-500/20 transition-all">
              <FolderOpen className="h-4 w-4 text-orange-400" />
            </div>
            <h3 className="truncate text-sm font-bold text-white leading-snug line-clamp-2">
              {project.name}
            </h3>
          </div>
          <ProjectStatusBadge status={project.status} />
        </div>

        {/* Description */}
        {project.description && (
          <p className="mb-4 flex-1 text-xs leading-relaxed text-zinc-600 line-clamp-2">
            {project.description}
          </p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-white/[0.05] pt-3">
          <span className="text-xs text-zinc-600">{formatRelative(project.created_at)}</span>
          <ArrowRight className="h-3.5 w-3.5 text-zinc-700 transition-all group-hover:text-orange-400 group-hover:translate-x-0.5" />
        </div>
      </div>
    </Link>
  )
}
