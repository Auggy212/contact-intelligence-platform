"use client"

import { useCallback, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useDropzone } from "react-dropzone"
import { useDocuments, useUploadDocument, useDeleteDocument } from "@/lib/hooks/use-documents"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
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
import { formatBytes } from "@/lib/utils"
import { FILE_ROLE_LABELS } from "@/lib/types/api"
import type { FileRole, ProjectFile } from "@/lib/types/api"
import {
  Upload, FileText, CheckCircle2, AlertCircle, Loader2, Trash2, Play,
} from "lucide-react"
import { cn } from "@/lib/utils"

const FILE_ROLES: FileRole[] = ["A", "B", "C"]

// Dark tinted surfaces + a coloured left accent per role (readable on ink).
const roleAccent: Record<FileRole, string> = {
  A: "border-sev-low-border bg-sev-low-bg/40",
  B: "border-success-border bg-success-bg/40",
  C: "border-sev-medium-border bg-sev-medium-bg/40",
}

const roleIconColor: Record<FileRole, string> = {
  A: "text-sev-low bg-sev-low-bg",
  B: "text-success bg-success-bg",
  C: "text-sev-medium bg-sev-medium-bg",
}

function ConfirmDeleteFile({
  file,
  open,
  onOpenChange,
  onConfirm,
  isPending,
}: {
  file: ProjectFile | null
  open: boolean
  onOpenChange: (v: boolean) => void
  onConfirm: () => void
  isPending: boolean
}) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Remove &ldquo;{file?.original_filename}&rdquo;?</AlertDialogTitle>
          <AlertDialogDescription>
            This will permanently delete the file and all its parsed clause data from the database and storage.
            Any analysis tasks that used this file will need to be re-run.
            This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={isPending}
            className="bg-red-600 hover:bg-red-700"
          >
            {isPending ? "Removing…" : "Yes, remove file"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

function UploadZone({ role, projectId }: { role: FileRole; projectId: string }) {
  const { data: documents } = useDocuments(projectId)
  const { mutate: upload, isPending: uploading } = useUploadDocument(projectId)
  const { mutateAsync: deleteDoc, isPending: deleting } = useDeleteDocument(projectId)
  const [progress, setProgress] = useState(0)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const roleInfo = FILE_ROLE_LABELS[role]

  const existing = documents?.find((d) => d.file_role === role) ?? null
  const parseStatus = existing?.parse_status

  const onDrop = useCallback(
    (files: File[]) => {
      if (!files[0]) return
      setProgress(0)
      upload({ fileRole: role, file: files[0], onProgress: setProgress })
    },
    [role, upload]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/pdf": [".pdf"],
    },
    maxFiles: 1,
    disabled: uploading || !!existing,
  })

  async function handleDelete() {
    if (!existing) return
    await deleteDoc(existing.id)
    setConfirmOpen(false)
  }

  return (
    <>
      <Card className={cn("border-2", roleAccent[role])}>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2.5">
            <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold", roleIconColor[role])}>
              {role}
            </div>
            <div>
              <CardTitle className="text-sm">{roleInfo.label}</CardTitle>
              <p className="text-xs text-slate-500 mt-0.5">{roleInfo.description}</p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {existing ? (
            <div className="space-y-3">
              <div className="flex items-start gap-3 p-3 rounded-lg bg-background/60 border border-border">
                <FileText className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">{existing.original_filename}</p>
                  <p className="text-xs text-slate-500">{formatBytes(existing.file_size_bytes)}</p>
                  <p className={cn(
                    "text-xs mt-0.5 flex items-center gap-1",
                    parseStatus === "completed" ? "text-green-600" : parseStatus === "failed" ? "text-red-600" : "text-blue-600"
                  )}>
                    <ParseStatusIcon status={parseStatus!} />
                    {parseStatus === "completed" ? "Parsed successfully" : parseStatus === "failed" ? "Parse failed" : "Parsing…"}
                  </p>
                </div>
              </div>

              <Button
                variant="outline"
                size="sm"
                className="w-full gap-2 text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700 hover:border-red-300"
                onClick={() => setConfirmOpen(true)}
                disabled={deleting}
              >
                {deleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                Remove &amp; replace file
              </Button>
            </div>
          ) : (
            <div
              {...getRootProps()}
              className={cn(
                "border-2 border-dashed rounded-lg p-6 flex flex-col items-center gap-2 cursor-pointer transition-colors",
                isDragActive ? "border-primary bg-primary/10" : "border-border hover:border-primary/40 hover:bg-secondary/50"
              )}
            >
              <input {...getInputProps()} />
              {uploading ? (
                <>
                  <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
                  <p className="text-xs text-slate-600">Uploading…</p>
                  <Progress value={progress} className="h-1.5 w-full" />
                </>
              ) : (
                <>
                  <Upload className="w-6 h-6 text-slate-400" />
                  <p className="text-xs font-medium text-slate-700">
                    {isDragActive ? "Drop here" : "Drag & drop or click to upload"}
                  </p>
                  <p className="text-xs text-slate-400">.docx or .pdf</p>
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmDeleteFile
        file={existing}
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        onConfirm={handleDelete}
        isPending={deleting}
      />
    </>
  )
}

function ParseStatusIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
  if (status === "failed") return <AlertCircle className="w-3.5 h-3.5 text-red-500" />
  return <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />
}

export default function UploadPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const router = useRouter()
  const { data: documents, isLoading } = useDocuments(projectId)

  const allReady = FILE_ROLES.every((r) =>
    documents?.some((d) => d.file_role === r && d.parse_status === "completed")
  )

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-semibold text-slate-900 mb-1">Upload Contract Documents</h2>
        <p className="text-sm text-slate-500">
          Upload all three document roles. To replace a file, click &ldquo;Remove &amp; replace&rdquo; then upload a new one.
          All must be parsed before you can run analysis.
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-48 rounded-lg" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {FILE_ROLES.map((role) => (
            <UploadZone key={role} role={role} projectId={projectId} />
          ))}
        </div>
      )}

      <div className="flex justify-end">
        <Button
          disabled={!allReady}
          onClick={() => router.push(`/projects/${projectId}/analysis`)}
        >
          <Play className="w-4 h-4 mr-2" />
          Proceed to Analysis
        </Button>
      </div>
    </div>
  )
}
