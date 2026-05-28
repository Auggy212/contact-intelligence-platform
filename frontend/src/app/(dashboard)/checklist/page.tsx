"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useChecklist, useCreateRule, useUpdateRule, useDeleteRule } from "@/lib/hooks/use-checklist"
import { PageHeader } from "@/components/shared/page-header"
import { EmptyState } from "@/components/shared/empty-state"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { SeverityBadge } from "@/components/findings/severity-badge"
import { CheckSquare, Plus, Pencil, Trash2, Loader2 } from "lucide-react"
import { useStaggerReveal } from "@/hooks/use-scroll-reveal"
import { cn } from "@/lib/utils"
import type { ChecklistRule, Severity } from "@/lib/types/api"

const RULE_TYPES = ["numeric_range", "max_value", "min_value", "string_allowlist", "date_future", "date_past", "boolean_present"] as const
type RuleType = typeof RULE_TYPES[number]

const schema = z.object({
  rule_code: z.string().min(1).max(16),
  name: z.string().min(1).max(256),
  description: z.string().optional(),
  severity: z.enum(["critical", "high", "medium", "low"]),
  rule_type: z.enum(RULE_TYPES),
  is_enabled: z.boolean().default(true),
  cfg_min: z.string().optional(),
  cfg_max: z.string().optional(),
  cfg_allowed: z.string().optional(),
  cfg_field: z.string().optional(),
})
type FormValues = z.infer<typeof schema>

function buildConfig(values: FormValues): Record<string, unknown> {
  const base = { type: values.rule_type }
  switch (values.rule_type) {
    case "numeric_range": return { ...base, min: Number(values.cfg_min), max: Number(values.cfg_max) }
    case "max_value": return { ...base, max: Number(values.cfg_max) }
    case "min_value": return { ...base, min: Number(values.cfg_min) }
    case "string_allowlist": return { ...base, allowed_values: values.cfg_allowed?.split(",").map((s) => s.trim()) }
    case "boolean_present": return { ...base, field_name: values.cfg_field }
    default: return base
  }
}

function RuleFormDialog({
  open, onOpenChange, editing,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  editing?: ChecklistRule | null
}) {
  const { mutateAsync: create, isPending: creating } = useCreateRule()
  const { mutateAsync: updateRule, isPending: updatingRule } = useUpdateRule()
  const isLoading = creating || updatingRule

  const existingType = editing?.rule_config?.type as RuleType | undefined
  const { register, handleSubmit, watch, reset, setValue, formState: { errors } } = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as any,
    defaultValues: editing ? {
      rule_code: editing.rule_code,
      name: editing.name,
      description: editing.description ?? "",
      severity: editing.severity as "critical" | "high" | "medium" | "low",
      rule_type: (existingType ?? "numeric_range") as RuleType,
      is_enabled: editing.is_enabled,
    } : { is_enabled: true, severity: "medium", rule_type: "numeric_range" },
  })

  const ruleType = watch("rule_type")

  async function onSubmit(v: FormValues) {
    const config = buildConfig(v)
    if (editing) {
      await updateRule({ id: editing.id, data: { name: v.name, description: v.description, severity: v.severity as Severity, rule_config: config, is_enabled: v.is_enabled } })
    } else {
      await create({ rule_code: v.rule_code, name: v.name, description: v.description, severity: v.severity as Severity, rule_config: config, is_enabled: v.is_enabled })
    }
    reset()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg border-white/[0.08] bg-[#111111] text-white animate-scale-in">
        <DialogHeader>
          <DialogTitle className="text-white">{editing ? "Edit Rule" : "New Checklist Rule"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="mt-2 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-zinc-300">Rule Code *</Label>
              <Input placeholder="e.g. NOTICE_90" className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60" {...register("rule_code")} disabled={!!editing} />
              {errors.rule_code && <p className="text-xs text-red-400">{errors.rule_code.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label className="text-zinc-300">Severity *</Label>
              <Select defaultValue={editing?.severity ?? "medium"} onValueChange={(v) => setValue("severity", v as "critical" | "high" | "medium" | "low")}>
                <SelectTrigger className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-zinc-300">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-white/[0.08] bg-[#1C1E26]">
                  {(["critical", "high", "medium", "low"] as const).map((s) => (
                    <SelectItem key={s} value={s} className="capitalize text-zinc-300">{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label className="text-zinc-300">Name *</Label>
            <Input placeholder="Rule display name" className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60" {...register("name")} />
          </div>
          <div className="space-y-1.5">
            <Label className="text-zinc-300">Description</Label>
            <Textarea rows={2} placeholder="What does this rule check?" className="rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60 resize-none" {...register("description")} />
          </div>
          <div className="space-y-1.5">
            <Label className="text-zinc-300">Rule Type *</Label>
            <Select defaultValue={existingType ?? "numeric_range"} onValueChange={(v) => setValue("rule_type", v as RuleType)}>
              <SelectTrigger className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-zinc-300">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-white/[0.08] bg-[#1C1E26]">
                {RULE_TYPES.map((t) => <SelectItem key={t} value={t} className="text-zinc-300">{t}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {/* Dynamic config */}
          {(ruleType === "numeric_range" || ruleType === "min_value") && (
            <div className="space-y-1.5"><Label className="text-zinc-300">Min Value</Label><Input type="number" className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white focus:border-orange-500/60" {...register("cfg_min")} /></div>
          )}
          {(ruleType === "numeric_range" || ruleType === "max_value") && (
            <div className="space-y-1.5"><Label className="text-zinc-300">Max Value</Label><Input type="number" className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white focus:border-orange-500/60" {...register("cfg_max")} /></div>
          )}
          {ruleType === "string_allowlist" && (
            <div className="space-y-1.5"><Label className="text-zinc-300">Allowed Values (comma-separated)</Label><Input placeholder="Mumbai, Delhi, Pune" className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white focus:border-orange-500/60" {...register("cfg_allowed")} /></div>
          )}
          {ruleType === "boolean_present" && (
            <div className="space-y-1.5"><Label className="text-zinc-300">Field Name</Label><Input placeholder="e.g. termination_clause" className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white focus:border-orange-500/60" {...register("cfg_field")} /></div>
          )}
          <div className="flex items-center gap-2 pt-1">
            <Switch defaultChecked={editing?.is_enabled ?? true} onCheckedChange={(v) => setValue("is_enabled", v)} />
            <Label className="text-zinc-300 cursor-pointer select-none">Enabled</Label>
          </div>
          <DialogFooter className="gap-2">
            <button type="button" onClick={() => onOpenChange(false)}
              className="flex h-10 items-center rounded-xl border border-white/[0.1] bg-white/[0.04] px-4 text-sm font-medium text-zinc-300 hover:text-white transition-all hover:bg-white/[0.06] active:scale-[0.98]">
              Cancel
            </button>
            <button type="submit" disabled={isLoading}
              className="flex h-10 items-center gap-2 rounded-xl bg-orange-500 px-4 text-sm font-bold text-white hover:bg-orange-400 active:scale-[0.98] disabled:opacity-50 hover:scale-[1.02]">
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {isLoading ? "Saving…" : editing ? "Save Changes" : "Create Rule"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default function ChecklistPage() {
  const { data: rules, isLoading } = useChecklist()
  const { mutate: deleteRule, isPending: deleting } = useDeleteRule()
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<ChecklistRule | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const revealRef = useStaggerReveal<HTMLTableSectionElement>(45)

  return (
    <div>
      <div className="animate-fade-up">
        <PageHeader
          title="Checklist Rules"
          description="Business rules applied during checklist validation against Indian law requirements"
          action={
            <button onClick={() => { setEditing(null); setFormOpen(true) }}
              className="flex h-9 items-center gap-2 rounded-xl bg-orange-500 px-4 text-sm font-bold text-white shadow-lg shadow-orange-500/20 transition-all hover:bg-orange-400 hover:scale-[1.02] active:scale-[0.98] animate-glow-pulse">
              <Plus className="w-4 h-4 mr-2" />Add Rule
            </button>
          }
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-lg" />)}</div>
      ) : !rules?.length ? (
        <div className="animate-fade-in delay-75">
          <EmptyState icon={CheckSquare} title="No checklist rules" description="Add custom rules to validate contract terms" action={{ label: "Add Rule", onClick: () => setFormOpen(true) }} />
        </div>
      ) : (
        <div className="rounded-2xl border border-white/[0.07] bg-[#111111] overflow-hidden animate-scale-in delay-75 hover:border-white/[0.1] transition-all duration-300">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-widest text-zinc-600">Code</th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-widest text-zinc-600">Name</th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-widest text-zinc-600">Severity</th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-widest text-zinc-600 hidden md:table-cell">Type</th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-widest text-zinc-600">Status</th>
                <th className="px-4 py-3 w-24" />
              </tr>
            </thead>
            <tbody ref={revealRef}>
              {rules.map((rule) => (
                <tr key={rule.id} className="reveal border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] transition-all duration-200">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <code className="text-xs bg-orange-500/12 text-orange-400 border border-orange-500/20 px-1.5 py-0.5 rounded font-mono">{rule.rule_code}</code>
                      {rule.is_default && <Badge variant="outline" className="text-xs border-zinc-700 bg-zinc-800 text-zinc-400">Default</Badge>}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-semibold text-white">{rule.name}</td>
                  <td className="px-4 py-3"><SeverityBadge severity={rule.severity} /></td>
                  <td className="px-4 py-3 text-xs text-zinc-500 hidden md:table-cell">{rule.rule_config.type as string}</td>
                  <td className="px-4 py-3">
                    <span className={cn("text-xs px-2 py-0.5 rounded-full border capitalize font-medium", rule.is_enabled ? "bg-emerald-500/12 text-emerald-400 border-emerald-500/20" : "bg-zinc-800 text-zinc-500 border-zinc-700")}>
                      {rule.is_enabled ? "Enabled" : "Disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <button onClick={() => { setEditing(rule); setFormOpen(true) }}
                        className="flex h-7 w-7 items-center justify-center rounded-lg text-zinc-600 hover:bg-white/[0.06] hover:text-orange-400 transition-all duration-200 hover:scale-110 active:scale-90">
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      {!rule.is_default && (
                        <button onClick={() => setDeleteId(rule.id)}
                          className="flex h-7 w-7 items-center justify-center rounded-lg text-zinc-700 hover:bg-red-500/10 hover:text-red-400 transition-all duration-200 hover:scale-110 active:scale-90">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <RuleFormDialog open={formOpen} onOpenChange={setFormOpen} editing={editing} />
      <ConfirmDialog
        open={!!deleteId}
        onOpenChange={(v) => !v && setDeleteId(null)}
        title="Delete Rule"
        description="This rule will no longer be applied during checklist validation. This cannot be undone."
        confirmLabel="Delete"
        onConfirm={() => { if (deleteId) { deleteRule(deleteId); setDeleteId(null) } }}
        loading={deleting}
      />
    </div>
  )
}
