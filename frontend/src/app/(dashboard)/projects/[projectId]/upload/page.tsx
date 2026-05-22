"use client"

import { useCallback, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useDropzone } from "react-dropzone"
import { useDocuments, useUploadDocument } from "@/lib/hooks/use-documents"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { formatBytes } from "@/lib/utils"
import { FILE_ROLE_LABELS } from "@/lib/types/api"
import type { FileRole } from "@/lib/types/api"
import {
  Upload, FileText, CheckCircle2, AlertCircle, Loader2, RefreshCw, Play,
} from "lucide-react"
import { cn } from "@/lib/utils"

const FILE_ROLES: FileRole[] = ["A", "B", "C"]

const roleAccent: Record<FileRole, string> = {
  A: "border-blue-200 bg-blue-50/50",
  B: "border-green-200 bg-green-50/50",
  C: "border-orange-200 bg-orange-50/50",
}

const roleIconColor: Record<FileRole, string> = {
  A: "text-blue-600 bg-blue-100",
  B: "text-green-600 bg-green-100",
  C: "text-orange-600 bg-orange-100",
}

function UploadZone({ role, projectId }: { role: FileRole; projectId: string }) {
  const { data: documents } = useDocuments(projectId)
  const { mutate: upload, isPending } = useUploadDocument(projectId)
  const [progress, setProgress] = useState(0)
  const roleInfo = FILE_ROLE_LABELS[role]

  const existing = documents?.find((d) => d.file_role === role)

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
    accept: { "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"], "application/pdf": [".pdf"] },
    maxFiles: 1,
    disabled: isPending,
  })

  const parseStatus = existing?.parse_status

  return (
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
            <div className="flex items-start gap-3 p-3 rounded-lg bg-white border">
              <FileText className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{existing.original_filename}</p>
                <p className="text-xs text-slate-500">{formatBytes(existing.file_size_bytes)}</p>
              </div>
              <ParseStatusIcon status={parseStatus!} />
            </div>
            {isPending && <Progress value={progress} className="h-1.5" />}
            <div
              {...getRootProps()}
              className="flex items-center justify-center gap-2 py-2 border border-dashed rounded-lg cursor-pointer hover:bg-white/50 transition-colors text-xs text-slate-500"
            >
              <input {...getInputProps()} />
              <RefreshCw className="w-3.5 h-3.5" />
              Replace file
            </div>
          </div>
        ) : (
          <div
            {...getRootProps()}
            className={cn(
              "border-2 border-dashed rounded-lg p-6 flex flex-col items-center gap-2 cursor-pointer transition-colors",
              isDragActive ? "border-blue-400 bg-blue-50" : "border-slate-200 hover:border-slate-300 hover:bg-white/50"
            )}
          >
            <input {...getInputProps()} />
            {isPending ? (
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
  )
}

function ParseStatusIcon({ status }: { status: string }) {
  if (status === "completed")
    return <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
  if (status === "failed")
    return <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
  return <Loader2 className="w-4 h-4 text-blue-500 animate-spin shrink-0" />
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
          Upload all three document roles. All must be parsed before you can run analysis.
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
