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
import { CheckSquare, Plus, Pencil, Trash2 } from "lucide-react"
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
  const { mutateAsync: update, isPending: updating } = useUpdateRule()
  const isLoading = creating || updating

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
      await update({ id: editing.id, data: { name: v.name, description: v.description, severity: v.severity as Severity, rule_config: config, is_enabled: v.is_enabled } })
    } else {
      await create({ rule_code: v.rule_code, name: v.name, description: v.description, severity: v.severity as Severity, rule_config: config, is_enabled: v.is_enabled })
    }
    reset()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit Rule" : "New Checklist Rule"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Rule Code *</Label>
              <Input placeholder="e.g. NOTICE_90" {...register("rule_code")} disabled={!!editing} />
              {errors.rule_code && <p className="text-xs text-red-500">{errors.rule_code.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Severity *</Label>
              <Select defaultValue={editing?.severity ?? "medium"} onValueChange={(v) => setValue("severity", v as "critical" | "high" | "medium" | "low")}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(["critical", "high", "medium", "low"] as const).map((s) => (
                    <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Name *</Label>
            <Input placeholder="Rule display name" {...register("name")} />
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Textarea rows={2} placeholder="What does this rule check?" {...register("description")} />
          </div>
          <div className="space-y-1.5">
            <Label>Rule Type *</Label>
            <Select defaultValue={existingType ?? "numeric_range"} onValueChange={(v) => setValue("rule_type", v as RuleType)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {RULE_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {/* Dynamic config */}
          {(ruleType === "numeric_range" || ruleType === "min_value") && (
            <div className="space-y-1.5"><Label>Min Value</Label><Input type="number" {...register("cfg_min")} /></div>
          )}
          {(ruleType === "numeric_range" || ruleType === "max_value") && (
            <div className="space-y-1.5"><Label>Max Value</Label><Input type="number" {...register("cfg_max")} /></div>
          )}
          {ruleType === "string_allowlist" && (
            <div className="space-y-1.5"><Label>Allowed Values (comma-separated)</Label><Input placeholder="Mumbai, Delhi, Pune" {...register("cfg_allowed")} /></div>
          )}
          {ruleType === "boolean_present" && (
            <div className="space-y-1.5"><Label>Field Name</Label><Input placeholder="e.g. termination_clause" {...register("cfg_field")} /></div>
          )}
          <div className="flex items-center gap-2">
            <Switch defaultChecked={editing?.is_enabled ?? true} onCheckedChange={(v) => setValue("is_enabled", v)} />
            <Label>Enabled</Label>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={isLoading}>{isLoading ? "Saving…" : editing ? "Save Changes" : "Create Rule"}</Button>
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

  return (
    <div>
      <PageHeader
        title="Checklist Rules"
        description="Business rules applied during checklist validation against Indian law requirements"
        action={
          <Button onClick={() => { setEditing(null); setFormOpen(true) }}>
            <Plus className="w-4 h-4 mr-2" />Add Rule
          </Button>
        }
      />

      {isLoading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-lg" />)}</div>
      ) : !rules?.length ? (
        <EmptyState icon={CheckSquare} title="No checklist rules" description="Add custom rules to validate contract terms" action={{ label: "Add Rule", onClick: () => setFormOpen(true) }} />
      ) : (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Code</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Severity</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Type</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                <th className="px-4 py-3 w-24" />
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id} className="border-b last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded font-mono">{rule.rule_code}</code>
                      {rule.is_default && <Badge variant="outline" className="text-xs text-slate-500">Default</Badge>}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-900">{rule.name}</td>
                  <td className="px-4 py-3"><SeverityBadge severity={rule.severity} /></td>
                  <td className="px-4 py-3 text-xs text-slate-500 hidden md:table-cell">{rule.rule_config.type as string}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${rule.is_enabled ? "bg-green-50 text-green-700 border-green-200" : "bg-slate-100 text-slate-500 border-slate-200"}`}>
                      {rule.is_enabled ? "Enabled" : "Disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => { setEditing(rule); setFormOpen(true) }}>
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      {!rule.is_default && (
                        <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-500 hover:text-red-600" onClick={() => setDeleteId(rule.id)}>
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
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
