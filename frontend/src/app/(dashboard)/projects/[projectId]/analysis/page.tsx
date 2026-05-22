"use client"

import { useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useTriggerTasks, useTaskPolling } from "@/lib/hooks/use-tasks"
import { useDocuments } from "@/lib/hooks/use-documents"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { TASK_TYPE_LABELS } from "@/lib/types/api"
import type { AnalysisTask, TaskType } from "@/lib/types/api"
import {
  Loader2, CheckCircle2, XCircle, Clock, Play, Flag, AlertTriangle,
} from "lucide-react"
import { cn } from "@/lib/utils"

const ALL_TASKS: TaskType[] = [
  "template_comparison",
  "vendor_diff",
  "law_validation",
  "checklist_validation",
]

function TaskStatusCard({ task }: { task: AnalysisTask }) {
  const { data: latest } = useTaskPolling(
    task.id,
    task.status === "queued" || task.status === "running"
  )
  const current = latest ?? task
  const info = TASK_TYPE_LABELS[current.task_type]

  return (
    <div className={cn(
      "flex items-start gap-3 p-4 rounded-lg border transition-colors",
      current.status === "completed" && "bg-green-50 border-green-200",
      current.status === "failed" && "bg-red-50 border-red-200",
      (current.status === "queued" || current.status === "running") && "bg-blue-50 border-blue-200",
    )}>
      <StatusIcon status={current.status} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-900">{info.label}</p>
        <p className="text-xs text-slate-500 mt-0.5">{info.description}</p>
        {current.status === "failed" && current.error_message && (
          <p className="text-xs text-red-600 mt-1">{current.error_message}</p>
        )}
        {current.status === "running" && (
          <p className="text-xs text-blue-600 mt-1 flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin" />
            Analyzing…
          </p>
        )}
      </div>
      <span className={cn(
        "text-xs font-medium capitalize px-2 py-0.5 rounded-full",
        current.status === "completed" && "bg-green-100 text-green-700",
        current.status === "failed" && "bg-red-100 text-red-700",
        current.status === "running" && "bg-blue-100 text-blue-700",
        current.status === "queued" && "bg-slate-100 text-slate-600",
      )}>
        {current.status}
      </span>
    </div>
  )
}

function StatusIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0 mt-0.5" />
  if (status === "failed") return <XCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
  if (status === "running") return <Loader2 className="w-5 h-5 text-blue-500 shrink-0 mt-0.5 animate-spin" />
  return <Clock className="w-5 h-5 text-slate-400 shrink-0 mt-0.5" />
}

export default function AnalysisPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const router = useRouter()
  const { data: documents } = useDocuments(projectId)
  const [selected, setSelected] = useState<Set<TaskType>>(new Set(ALL_TASKS))
  const [tasks, setTasks] = useState<AnalysisTask[]>([])
  const { mutateAsync: trigger, isPending } = useTriggerTasks(projectId)

  const hasAllDocs = ["A", "B", "C"].every(
    (r) => documents?.some((d) => d.file_role === r && d.parse_status === "completed")
  )

  function toggleTask(t: TaskType) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(t)) { next.delete(t) } else { next.add(t) }
      return next
    })
  }

  async function handleRun() {
    const result = await trigger({ task_types: Array.from(selected) })
    setTasks(result)
  }

  const allDone = tasks.length > 0 && tasks.every((t) => t.status === "completed" || t.status === "failed")

  return (
    <div className="space-y-6 max-w-2xl">
      {!hasAllDocs && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>All three documents must be uploaded and parsed before running analysis.</span>
        </div>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Select Analysis Tasks</CardTitle>
        </CardHeader>
        <CardContent className="pt-0 space-y-3">
          {ALL_TASKS.map((taskType) => {
            const info = TASK_TYPE_LABELS[taskType]
            return (
              <div key={taskType} className="flex items-start gap-3 p-3 rounded-lg hover:bg-slate-50 transition-colors">
                <Checkbox
                  id={taskType}
                  checked={selected.has(taskType)}
                  onCheckedChange={() => toggleTask(taskType)}
                  disabled={!hasAllDocs || isPending || tasks.length > 0}
                />
                <div>
                  <Label htmlFor={taskType} className="text-sm font-medium cursor-pointer">{info.label}</Label>
                  <p className="text-xs text-slate-500 mt-0.5">{info.description}</p>
                </div>
              </div>
            )
          })}
          <Button
            onClick={handleRun}
            disabled={!hasAllDocs || isPending || tasks.length > 0 || selected.size === 0}
            className="w-full mt-2"
          >
            {isPending ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Starting…</>
            ) : (
              <><Play className="w-4 h-4 mr-2" />Run {selected.size} Task{selected.size !== 1 ? "s" : ""}</>
            )}
          </Button>
        </CardContent>
      </Card>

      {tasks.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Task Status</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 space-y-3">
            {tasks.map((task) => <TaskStatusCard key={task.id} task={task} />)}
            {allDone && (
              <Button
                onClick={() => router.push(`/projects/${projectId}/findings`)}
                className="w-full mt-2"
              >
                <Flag className="w-4 h-4 mr-2" />
                View Findings
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
