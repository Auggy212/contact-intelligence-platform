"use client"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
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
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete &ldquo;{project?.name}&rdquo;?</AlertDialogTitle>
          <AlertDialogDescription className="space-y-2">
            <span className="block">
              This will permanently delete the project and all associated data, including:
            </span>
            <ul className="list-disc list-inside text-sm space-y-0.5 text-slate-600">
              <li>All uploaded documents (Template A, Draft B, Vendor C) from storage</li>
              <li>All parsed clause data</li>
              <li>All analysis tasks and AI findings</li>
              <li>All review decisions (approved / rejected)</li>
            </ul>
            <span className="block text-xs text-slate-500 mt-2">
              Audit log entries are retained for compliance and cannot be deleted.
            </span>
            <span className="block font-medium text-slate-800 mt-1">
              Everything else is permanently removed and cannot be recovered.
            </span>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={isPending}
            className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
          >
            {isPending ? "Deleting…" : "Yes, delete permanently"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
