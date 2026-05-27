"use client"

import { Fragment, useEffect, useState } from "react"
import { useForm, Controller } from "react-hook-form"
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
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { SeverityBadge } from "@/components/findings/severity-badge"
import { CheckSquare, Plus, Pencil, Trash2, ChevronDown } from "lucide-react"
import type { ChecklistRule, Severity } from "@/lib/types/api"

const RULE_TYPES = ["numeric_range", "max_value", "min_value", "string_allowlist", "date_future", "date_past", "boolean_present"] as const
type RuleType = typeof RULE_TYPES[number]

const RULE_TYPE_LABELS: Record<RuleType, string> = {
  numeric_range: "Numeric Range",
  max_value: "Max Value",
  min_value: "Min Value",
  string_allowlist: "Allowed Values List",
  date_future: "Date (must be future)",
  date_past: "Date (must be past)",
  boolean_present: "Must Be Present",
}

// What fields each rule type can use
const FIELD_OPTIONS = [
  { value: "agreement_duration_months", label: "Agreement Duration (months)" },
  { value: "agreement_date", label: "Agreement Date" },
  { value: "dispute_court_city", label: "Dispute Court City" },
  { value: "advance_payment_percent", label: "Advance Payment (%)" },
  { value: "contract_value_inr", label: "Contract Value (INR)" },
  { value: "termination_notice_months", label: "Termination Notice (months)" },
]

const schema = z.object({
  rule_code: z.string().min(1).max(16),
  name: z.string().min(1).max(256),
  description: z.string().optional(),
  severity: z.enum(["critical", "high", "medium", "low"]),
  rule_type: z.enum(RULE_TYPES),
  field: z.string().optional(),
  is_enabled: z.boolean().default(true),
  cfg_min: z.string().optional(),
  cfg_max: z.string().optional(),
  cfg_allowed: z.string().optional(),
})
type FormValues = z.infer<typeof schema>

function buildConfig(values: FormValues): Record<string, unknown> {
  const base: Record<string, unknown> = { type: values.rule_type }
  if (values.field) base.field = values.field

  switch (values.rule_type) {
    case "numeric_range":
      if (values.cfg_min) base.min = Number(values.cfg_min)
      if (values.cfg_max) base.max = Number(values.cfg_max)
      break
    case "max_value":
      if (values.cfg_max) base.max = Number(values.cfg_max)
      break
    case "min_value":
      if (values.cfg_min) base.min = Number(values.cfg_min)
      break
    case "string_allowlist":
      base.allowed_values = values.cfg_allowed?.split(",").map((s) => s.trim()).filter(Boolean)
      break
    case "boolean_present":
      break
    default:
      break
  }
  return base
}

function getDefaultsFromRule(rule: ChecklistRule): Partial<FormValues> {
  const cfg = rule.rule_config as Record<string, unknown>
  const ruleType = (cfg.type ?? "numeric_range") as RuleType
  return {
    rule_code: rule.rule_code,
    name: rule.name,
    description: rule.description ?? "",
    severity: rule.severity as "critical" | "high" | "medium" | "low",
    rule_type: ruleType,
    field: (cfg.field as string) ?? "",
    is_enabled: rule.is_enabled,
    cfg_min: cfg.min != null ? String(cfg.min) : "",
    cfg_max: cfg.max != null ? String(cfg.max) : "",
    cfg_allowed: Array.isArray(cfg.allowed_values) ? (cfg.allowed_values as string[]).join(", ") : "",
  }
}

const BLANK_DEFAULTS: FormValues = {
  rule_code: "",
  name: "",
  description: "",
  severity: "medium",
  rule_type: "numeric_range",
  field: "",
  is_enabled: true,
  cfg_min: "",
  cfg_max: "",
  cfg_allowed: "",
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

  const { register, handleSubmit, watch, reset, control, formState: { errors } } = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as any,
    defaultValues: BLANK_DEFAULTS,
  })

  // Re-populate form whenever the dialog opens or the editing target changes
  useEffect(() => {
    if (open) {
      reset(editing ? getDefaultsFromRule(editing) : BLANK_DEFAULTS)
    }
  }, [open, editing, reset])

  const ruleType = watch("rule_type")
  const needsField = !["boolean_present", "date_future", "date_past"].includes(ruleType)

  async function onSubmit(v: FormValues) {
    const config = buildConfig(v)
    if (editing) {
      await update({
        id: editing.id,
        data: {
          name: v.name,
          description: v.description,
          severity: v.severity as Severity,
          rule_config: config,
          is_enabled: v.is_enabled,
        },
      })
    } else {
      await create({
        rule_code: v.rule_code,
        name: v.name,
        description: v.description,
        severity: v.severity as Severity,
        rule_config: config,
        is_enabled: v.is_enabled,
      })
    }
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit Rule" : "New Checklist Rule"}</DialogTitle>
          <DialogDescription>
            {editing
              ? "Update the rule name, description, severity, thresholds, or enable/disable it."
              : "Define a validation rule that will run automatically during Checklist Validation."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Rule Code *</Label>
              <Input
                placeholder="e.g. NOTICE_90"
                {...register("rule_code")}
                disabled={!!editing}
                className={editing ? "bg-slate-50 text-slate-500" : ""}
              />
              {errors.rule_code && <p className="text-xs text-red-500">{errors.rule_code.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Severity *</Label>
              <Controller
                name="severity"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {(["critical", "high", "medium", "low"] as const).map((s) => (
                        <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Name *</Label>
            <Input placeholder="Rule display name" {...register("name")} />
            {errors.name && <p className="text-xs text-red-500">{errors.name.message}</p>}
          </div>

          <div className="space-y-1.5">
            <Label>Description</Label>
            <Textarea rows={2} placeholder="What does this rule check? What should the reviewer look for?" {...register("description")} />
          </div>

          <div className="space-y-1.5">
            <Label>Rule Type *</Label>
            <Controller
              name="rule_type"
              control={control}
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {RULE_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>{RULE_TYPE_LABELS[t]}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </div>

          {/* Which extracted field to validate against */}
          {needsField && (
            <div className="space-y-1.5">
              <Label>Contract Field to Check *</Label>
              <Controller
                name="field"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger><SelectValue placeholder="Select a field…" /></SelectTrigger>
                    <SelectContent>
                      {FIELD_OPTIONS.map((f) => (
                        <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              <p className="text-xs text-slate-400">Which value extracted from the contract to validate.</p>
            </div>
          )}

          {/* Dynamic config inputs */}
          {(ruleType === "numeric_range" || ruleType === "min_value") && (
            <div className="space-y-1.5">
              <Label>Min Value</Label>
              <Input type="number" placeholder="e.g. 12" {...register("cfg_min")} />
            </div>
          )}
          {(ruleType === "numeric_range" || ruleType === "max_value") && (
            <div className="space-y-1.5">
              <Label>Max Value</Label>
              <Input type="number" placeholder="e.g. 36" {...register("cfg_max")} />
            </div>
          )}
          {ruleType === "string_allowlist" && (
            <div className="space-y-1.5">
              <Label>Allowed Values (comma-separated)</Label>
              <Input placeholder="e.g. Mumbai, Delhi, Pune" {...register("cfg_allowed")} />
            </div>
          )}

          {/* Enabled toggle */}
          <Controller
            name="is_enabled"
            control={control}
            render={({ field }) => (
              <div className="flex items-center gap-2">
                <Switch checked={field.value} onCheckedChange={field.onChange} />
                <Label>Active — rule runs during Checklist Validation</Label>
              </div>
            )}
          />

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Saving…" : editing ? "Save Changes" : "Create Rule"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 }

export default function ChecklistPage() {
  const { data: rules, isLoading } = useChecklist()
  const { mutate: updateRule } = useUpdateRule()
  const { mutate: deleteRule, isPending: deleting } = useDeleteRule()
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<ChecklistRule | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const sorted = [...(rules ?? [])].sort((a, b) => {
    const sa = SEVERITY_ORDER[a.severity as keyof typeof SEVERITY_ORDER] ?? 99
    const sb = SEVERITY_ORDER[b.severity as keyof typeof SEVERITY_ORDER] ?? 99
    return sa - sb || a.rule_code.localeCompare(b.rule_code)
  })

  function toggleEnabled(rule: ChecklistRule) {
    updateRule({ id: rule.id, data: { is_enabled: !rule.is_enabled } })
  }

  return (
    <div>
      <PageHeader
        title="Checklist Rules"
        description="Rules run during Checklist Validation to catch contract issues. Disable a rule to exclude it from analysis."
        action={
          <Button onClick={() => { setEditing(null); setFormOpen(true) }}>
            <Plus className="w-4 h-4 mr-2" />Add Rule
          </Button>
        }
      />

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}
        </div>
      ) : !sorted.length ? (
        <EmptyState
          icon={CheckSquare}
          title="No checklist rules"
          description="Add rules to validate contract terms. Rules run automatically when you start a Checklist Validation task."
          action={{ label: "Add Rule", onClick: () => setFormOpen(true) }}
        />
      ) : (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide w-8" />
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Code</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Name &amp; Description</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Severity</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Active</th>
                <th className="px-4 py-3 w-20" />
              </tr>
            </thead>
            <tbody>
              {sorted.map((rule) => {
                const cfg = rule.rule_config as Record<string, unknown>
                const isExpanded = expandedId === rule.id
                const fieldLabel = FIELD_OPTIONS.find((f) => f.value === cfg.field)?.label ?? (cfg.field as string | undefined) ?? null

                return (
                  <Fragment key={rule.id}>
                    <tr
                      className={`border-b cursor-pointer transition-colors ${isExpanded ? "bg-blue-50" : "hover:bg-slate-50"} ${!rule.is_enabled ? "opacity-50" : ""}`}
                      onClick={() => setExpandedId(isExpanded ? null : rule.id)}
                    >
                      <td className="px-4 py-3 text-slate-400">
                        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded font-mono">{rule.rule_code}</code>
                          {rule.is_default && <Badge variant="outline" className="text-xs text-slate-500">Default</Badge>}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-900">{rule.name}</p>
                        {rule.description && (
                          <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{rule.description}</p>
                        )}
                      </td>
                      <td className="px-4 py-3"><SeverityBadge severity={rule.severity} /></td>
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <Switch
                          checked={rule.is_enabled}
                          onCheckedChange={() => toggleEnabled(rule)}
                          aria-label={rule.is_enabled ? "Disable rule" : "Enable rule"}
                        />
                      </td>
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-1 justify-end">
                          <Button
                            size="sm" variant="ghost" className="h-7 w-7 p-0"
                            onClick={() => { setEditing(rule); setFormOpen(true) }}
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </Button>
                          {!rule.is_default && (
                            <Button
                              size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-500 hover:text-red-600"
                              onClick={() => setDeleteId(rule.id)}
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>

                    {/* Expanded detail row */}
                    {isExpanded && (
                      <tr className="border-b bg-blue-50">
                        <td colSpan={6} className="px-6 pb-4 pt-0">
                          <div className="grid grid-cols-2 gap-4 text-sm border-t border-blue-100 pt-3">
                            <div>
                              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">What this rule checks</p>
                              <p className="text-slate-700">{rule.description ?? "No description provided."}</p>
                            </div>
                            <div>
                              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Thresholds &amp; config</p>
                              <div className="space-y-1">
                                {fieldLabel && (
                                  <p className="text-slate-600"><span className="font-medium">Checks:</span> {fieldLabel}</p>
                                )}
                                {cfg.min != null && (
                                  <p className="text-slate-600"><span className="font-medium">Min:</span> {String(cfg.min)}</p>
                                )}
                                {cfg.max != null && (
                                  <p className="text-slate-600"><span className="font-medium">Max:</span> {String(cfg.max)}</p>
                                )}
                                {cfg.min_months != null && (
                                  <p className="text-slate-600"><span className="font-medium">Min months:</span> {String(cfg.min_months)}</p>
                                )}
                                {cfg.max_months != null && (
                                  <p className="text-slate-600"><span className="font-medium">Max months:</span> {String(cfg.max_months)}</p>
                                )}
                                {cfg.max_percent != null && (
                                  <p className="text-slate-600"><span className="font-medium">Max %:</span> {String(cfg.max_percent)}%</p>
                                )}
                                {cfg.max_value_inr != null && (
                                  <p className="text-slate-600"><span className="font-medium">Max value:</span> ₹{Number(cfg.max_value_inr).toLocaleString("en-IN")}</p>
                                )}
                                {Array.isArray(cfg.allowed_cities) && (
                                  <p className="text-slate-600"><span className="font-medium">Allowed cities:</span> {(cfg.allowed_cities as string[]).join(", ")}</p>
                                )}
                                {Array.isArray(cfg.allowed_values) && (
                                  <p className="text-slate-600"><span className="font-medium">Allowed values:</span> {(cfg.allowed_values as string[]).join(", ")}</p>
                                )}
                                {!fieldLabel && cfg.min == null && cfg.max == null && cfg.min_months == null && cfg.max_months == null && cfg.max_percent == null && cfg.max_value_inr == null && !Array.isArray(cfg.allowed_cities) && !Array.isArray(cfg.allowed_values) && (
                                  <p className="text-slate-400 text-xs italic">Uses built-in extraction logic for this field.</p>
                                )}
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-3 text-xs text-slate-400">
        Click any row to see full rule details. Toggle the switch to enable or disable a rule without deleting it. Disabled rules are skipped during Checklist Validation.
      </p>

      <RuleFormDialog open={formOpen} onOpenChange={setFormOpen} editing={editing} />
      <ConfirmDialog
        open={!!deleteId}
        onOpenChange={(v) => !v && setDeleteId(null)}
        title="Delete Rule"
        description="This rule will no longer run during Checklist Validation. This cannot be undone."
        confirmLabel="Delete"
        onConfirm={() => { if (deleteId) { deleteRule(deleteId); setDeleteId(null) } }}
        loading={deleting}
      />
    </div>
  )
}
