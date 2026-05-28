"use client"

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { useDeleteProject } from "@/lib/hooks/use-projects"
import type { Project } from "@/lib/types/api"

interface DeleteProjectDialogProps {
  project: Project | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDeleted?: () => void
}

export function DeleteProjectDialog({ project, open, onOpenChange, onDeleted }: DeleteProjectDialogProps) {
  const { mutateAsync, isPending } = useDeleteProject()

  async function handleConfirm() {
    if (!project) return
    await mutateAsync(project.id)
    onOpenChange(false)
    onDeleted?.()
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="border-white/[0.08] bg-[#111111] text-white shadow-2xl">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-lg font-bold text-white">
            Delete &ldquo;{project?.name}&rdquo;?
          </AlertDialogTitle>
          <AlertDialogDescription className="space-y-3 text-zinc-400">
            <span className="block">This will permanently delete the project and all associated data, including:</span>
            <ul className="list-disc list-inside space-y-1 text-sm text-zinc-500">
              <li>All uploaded documents (Template A, Draft B, Vendor C) from storage</li>
              <li>All parsed clause data</li>
              <li>All analysis tasks and AI findings</li>
              <li>All review decisions (approved / rejected)</li>
            </ul>
            <span className="block text-xs text-zinc-600">
              Audit log entries are retained for compliance and cannot be deleted.
            </span>
            <span className="block font-semibold text-white">
              This action cannot be undone.
            </span>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel
            disabled={isPending}
            className="rounded-xl border-white/[0.1] bg-white/[0.04] text-zinc-300 hover:border-white/20 hover:bg-white/[0.06] hover:text-white"
          >
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={isPending}
            className="rounded-xl bg-red-600 text-white hover:bg-red-500 active:scale-[0.97]"
          >
            {isPending ? "Deleting…" : "Yes, delete permanently"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
