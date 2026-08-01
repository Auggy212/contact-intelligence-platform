"use client"

import { useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useTriggerTasks, useTaskPolling, useProjectTasks, useFindings } from "@/lib/hooks/use-tasks"
import { dedupeFindings } from "@/lib/findings-dedup"
import { useDocuments } from "@/lib/hooks/use-documents"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { TASK_TYPE_LABELS } from "@/lib/types/api"
import type { AnalysisTask, TaskType } from "@/lib/types/api"
import {
  Loader2, CheckCircle2, XCircle, Clock, Play, Flag, AlertTriangle, RefreshCw, History,
} from "lucide-react"
import { cn, formatRelative } from "@/lib/utils"

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
      "flex items-start gap-3 rounded-lg border p-4 transition-colors duration-200 ease-out-quint",
      current.status === "completed" && "border-success-border bg-success-bg",
      current.status === "failed" && "border-sev-critical-border bg-sev-critical-bg",
      (current.status === "queued" || current.status === "running") && "border-sev-low-border bg-sev-low-bg",
    )}>
      <StatusIcon status={current.status} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground">{info.label}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">{info.description}</p>
        {current.status === "failed" && current.error_message && (
          <p className="mt-1 text-xs text-sev-critical">{current.error_message}</p>
        )}
        {current.status === "running" && (
          <p className="mt-1 flex items-center gap-1 text-xs text-sev-low">
            <Loader2 className="h-3 w-3 animate-spin" />
            Analyzing…
          </p>
        )}
      </div>
      <span className={cn(
        "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
        current.status === "completed" && "bg-success/12 text-success",
        current.status === "failed" && "bg-sev-critical/12 text-sev-critical",
        current.status === "running" && "bg-sev-low/12 text-sev-low",
        current.status === "queued" && "bg-secondary text-muted-foreground",
      )}>
        {current.status}
      </span>
    </div>
  )
}

function StatusIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-success" />
  if (status === "failed") return <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-sev-critical" />
  if (status === "running") return <Loader2 className="mt-0.5 h-5 w-5 shrink-0 animate-spin text-sev-low" />
  return <Clock className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
}

// Groups existing tasks by type, picks the most recent per type
function latestByType(tasks: AnalysisTask[]): AnalysisTask[] {
  const seen = new Map<string, AnalysisTask>()
  for (const t of tasks) {
    if (!seen.has(t.task_type)) seen.set(t.task_type, t)
  }
  return Array.from(seen.values())
}

export default function AnalysisPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const router = useRouter()
  const { data: documents } = useDocuments(projectId)
  const { data: existingTasks, isLoading: tasksLoading } = useProjectTasks(projectId)
  const { data: findings } = useFindings(projectId)
  const [selected, setSelected] = useState<Set<TaskType>>(new Set(ALL_TASKS))
  const [currentRunTasks, setCurrentRunTasks] = useState<AnalysisTask[]>([])
  const { mutateAsync: trigger, isPending } = useTriggerTasks(projectId)

  const hasAllDocs = ["A", "B", "C"].every(
    (r) => documents?.some((d) => d.file_role === r && d.parse_status === "completed")
  )

  const isRunning = currentRunTasks.some((t) => t.status === "queued" || t.status === "running")
  const allDone = currentRunTasks.length > 0 && currentRunTasks.every((t) => t.status === "completed" || t.status === "failed")
  const hasRun = currentRunTasks.length > 0

  // Previous run summary from DB (exclude currently running tasks)
  const previousTasks = latestByType(existingTasks ?? [])
  const hasPreviousRun = previousTasks.length > 0
  const prevCompleted = previousTasks.filter((t) => t.status === "completed").length
  const prevFailed = previousTasks.filter((t) => t.status === "failed").length
  const mostRecentTask = previousTasks[0]
  const findingsCount = findings ? dedupeFindings(findings).length : 0

  function toggleTask(t: TaskType) {
    if (isRunning) return
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(t)) { next.delete(t) } else { next.add(t) }
      return next
    })
  }

  async function handleRun() {
    const result = await trigger({ task_types: Array.from(selected) })
    setCurrentRunTasks(result)
  }

  function handleRerun() {
    setCurrentRunTasks([])
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {!hasAllDocs && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>All three documents (Template A, Proposed Draft B, Vendor Reply C) must be uploaded and parsed before running analysis.</span>
        </div>
      )}

      {/* Previous run summary — shown when tasks have run before and no current run active */}
      {!hasRun && !tasksLoading && hasPreviousRun && (
        <Card className="border-slate-200">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-slate-500" />
              <CardTitle className="text-base">Previous Run</CardTitle>
              {mostRecentTask && (
                <span className="ml-auto text-xs text-slate-400">
                  {formatRelative(mostRecentTask.created_at)}
                </span>
              )}
            </div>
          </CardHeader>
          <CardContent className="pt-0 space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-slate-50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-slate-900">{previousTasks.length}</p>
                <p className="text-xs text-slate-500 mt-0.5">Tasks run</p>
              </div>
              <div className="bg-green-50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-green-700">{prevCompleted}</p>
                <p className="text-xs text-green-600 mt-0.5">Completed</p>
              </div>
              <div className="bg-blue-50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-blue-700">{findingsCount}</p>
                <p className="text-xs text-blue-600 mt-0.5">Issues</p>
              </div>
            </div>

            {prevFailed > 0 && (
              <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {prevFailed} task{prevFailed > 1 ? "s" : ""} failed in the last run.
              </p>
            )}

            <div className="space-y-1.5">
              {previousTasks.map((task) => {
                const info = TASK_TYPE_LABELS[task.task_type]
                return (
                  <div key={task.id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <StatusIcon status={task.status} />
                      <span className="text-slate-700">{info.label}</span>
                    </div>
                    <span className={cn(
                      "text-xs capitalize px-2 py-0.5 rounded-full font-medium",
                      task.status === "completed" && "bg-green-100 text-green-700",
                      task.status === "failed" && "bg-red-100 text-red-700",
                      task.status === "running" && "bg-blue-100 text-blue-700",
                      task.status === "queued" && "bg-slate-100 text-slate-600",
                    )}>
                      {task.status}
                    </span>
                  </div>
                )
              })}
            </div>

            {findingsCount > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => router.push(`/projects/${projectId}/findings`)}
              >
                <Flag className="w-3.5 h-3.5 mr-2" />
                View {findingsCount} finding{findingsCount !== 1 ? "s" : ""} from last run
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Task selection */}
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
                  disabled={!hasAllDocs || isRunning}
                />
                <div>
                  <Label htmlFor={taskType} className="text-sm font-medium cursor-pointer">{info.label}</Label>
                  <p className="text-xs text-slate-500 mt-0.5">{info.description}</p>
                </div>
              </div>
            )
          })}

          {!hasRun ? (
            <Button
              onClick={handleRun}
              disabled={!hasAllDocs || isPending || isRunning || selected.size === 0}
              className="w-full mt-2"
            >
              {isPending ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Starting…</>
              ) : (
                <><Play className="w-4 h-4 mr-2" />Run {selected.size} Task{selected.size !== 1 ? "s" : ""}</>
              )}
            </Button>
          ) : (
            <div className="flex gap-2 mt-2">
              <Button variant="outline" onClick={handleRerun} disabled={isRunning} className="flex-1">
                <RefreshCw className="w-4 h-4 mr-2" />
                Re-run Analysis
              </Button>
              {allDone && (
                <Button onClick={() => router.push(`/projects/${projectId}/findings`)} className="flex-1">
                  <Flag className="w-4 h-4 mr-2" />
                  View Findings
                </Button>
              )}
            </div>
          )}

          {allDone && (
            <p className="text-xs text-slate-400 text-center">
              Re-running will replace all previous findings for the selected tasks.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Current run live status */}
      {currentRunTasks.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Task Status</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 space-y-3">
            {currentRunTasks.map((task) => <TaskStatusCard key={task.id} task={task} />)}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
