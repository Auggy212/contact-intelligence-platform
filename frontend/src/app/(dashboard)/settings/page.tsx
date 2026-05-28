"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useOrganization } from "@/lib/hooks/use-organization"
import { useWorkspaces, useCreateWorkspace, useUpdateWorkspace } from "@/lib/hooks/use-organization"
import { PageHeader } from "@/components/shared/page-header"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { Building2, Plus, Pencil, FolderOpen, Globe, Save, Loader2 } from "lucide-react"
import { useStaggerReveal } from "@/hooks/use-scroll-reveal"
import type { Workspace } from "@/lib/types/api"

// ── Org settings ──────────────────────────────────────────────────────────────

const orgSchema = z.object({
  name: z.string().min(1, "Name is required").max(128),
  logo_url: z.string().url("Must be a valid URL").optional().or(z.literal("")),
})
type OrgForm = z.infer<typeof orgSchema>

function OrgSettingsCard() {
  const { data: org, isLoading, update, updating } = useOrganization()

  const { register, handleSubmit, formState: { errors, isDirty } } = useForm<OrgForm>({
    resolver: zodResolver(orgSchema),
    values: { name: org?.name ?? "", logo_url: org?.logo_url ?? "" },
  })

  function onSubmit(v: OrgForm) {
    update({ name: v.name, logo_url: v.logo_url || undefined })
  }

  return (
    <div className="rounded-2xl border border-white/[0.07] bg-[#111111] p-6 reveal transition-all duration-300 hover:border-white/[0.12]">
      <div className="mb-5 flex items-center gap-2">
        <Building2 className="h-4 w-4 text-orange-400" />
        <h3 className="text-sm font-bold text-white">Organisation Settings</h3>
      </div>
      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-9 w-full bg-white/[0.04]" />
          <Skeleton className="h-9 w-full bg-white/[0.04]" />
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label className="text-sm font-medium text-zinc-300">Organisation Name <span className="text-orange-400">*</span></Label>
            <Input placeholder="Acme Legal LLP"
              className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60 focus:ring-2 focus:ring-orange-500/10 transition-all duration-200"
              {...register("name")} />
            {errors.name && <p className="text-xs text-red-400">{errors.name.message}</p>}
          </div>
          <div className="space-y-2">
            <Label className="text-sm font-medium text-zinc-300">Logo URL</Label>
            <Input placeholder="https://cdn.example.com/logo.png"
              className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60 focus:ring-2 focus:ring-orange-500/10 transition-all duration-200"
              {...register("logo_url")} />
            {errors.logo_url && <p className="text-xs text-red-400">{errors.logo_url.message}</p>}
            <p className="text-xs text-zinc-600">Paste a public URL to your organisation&apos;s logo image</p>
          </div>
          {org?.slug && (
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-300">Organisation Slug</Label>
              <div className="flex h-11 items-center gap-2 rounded-xl border border-white/[0.08] bg-[#1C1E26] px-3 text-sm text-zinc-500">
                <Globe className="h-3.5 w-3.5 shrink-0" />
                <span className="font-mono">{org.slug}</span>
              </div>
              <p className="text-xs text-zinc-600">Slug is set by Clerk and cannot be changed here</p>
            </div>
          )}
          <div className="flex justify-end pt-1">
            <button type="submit" disabled={!isDirty || updating}
              className="flex h-10 items-center gap-2 rounded-xl bg-orange-500 px-5 text-sm font-bold text-white shadow-lg shadow-orange-500/20 transition-all hover:bg-orange-400 disabled:opacity-40 hover:scale-[1.02] active:scale-[0.98] animate-glow-pulse">
              {updating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {updating ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

// ── Workspace dialog ──────────────────────────────────────────────────────────

const wsSchema = z.object({
  name: z.string().min(1, "Name is required").max(128),
  description: z.string().optional(),
})
type WsForm = z.infer<typeof wsSchema>

function WorkspaceDialog({
  open,
  onOpenChange,
  editing,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  editing?: Workspace | null
}) {
  const { mutateAsync: create, isPending: creating } = useCreateWorkspace()
  const { mutateAsync: update, isPending: updating } = useUpdateWorkspace()
  const isPending = creating || updating

  const { register, handleSubmit, reset, formState: { errors } } = useForm<WsForm>({
    resolver: zodResolver(wsSchema),
    values: editing ? { name: editing.name, description: editing.description ?? "" } : { name: "", description: "" },
  })

  async function onSubmit(v: WsForm) {
    if (editing) {
      await update({ id: editing.id, data: { name: v.name, description: v.description } })
    } else {
      await create({ name: v.name, description: v.description })
    }
    reset()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm border-white/[0.08] bg-[#111111] text-white">
        <DialogHeader>
          <DialogTitle className="text-white">{editing ? "Edit Workspace" : "New Workspace"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="mt-2 space-y-4">
          <div className="space-y-2">
            <Label className="text-sm font-medium text-zinc-300">Name <span className="text-orange-400">*</span></Label>
            <Input placeholder="e.g. Mumbai Office"
              className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60 focus:ring-2 focus:ring-orange-500/10 transition-all duration-200"
              {...register("name")} />
            {errors.name && <p className="text-xs text-red-400">{errors.name.message}</p>}
          </div>
          <div className="space-y-2">
            <Label className="text-sm font-medium text-zinc-300">Description</Label>
            <Textarea rows={2} placeholder="Optional description"
              className="rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60 focus:ring-2 focus:ring-orange-500/10 transition-all duration-200 resize-none"
              {...register("description")} />
          </div>
          <DialogFooter className="gap-2">
            <button type="button" onClick={() => onOpenChange(false)}
              className="flex h-10 items-center rounded-xl border border-white/[0.1] bg-white/[0.04] px-4 text-sm font-medium text-zinc-300 hover:text-white transition-all hover:bg-white/[0.06] active:scale-[0.98]">
              Cancel
            </button>
            <button type="submit" disabled={isPending}
              className="flex h-10 items-center gap-2 rounded-xl bg-orange-500 px-4 text-sm font-bold text-white hover:bg-orange-400 active:scale-[0.98] disabled:opacity-50 hover:scale-[1.02]">
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {isPending ? "Saving…" : editing ? "Save Changes" : "Create"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ── Workspaces card ───────────────────────────────────────────────────────────

function WorkspacesCard() {
  const { data: workspaces, isLoading } = useWorkspaces()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Workspace | null>(null)

  return (
    <div className="rounded-2xl border border-white/[0.07] bg-[#111111] p-6 reveal transition-all duration-300 hover:border-white/[0.12]">
      <div className="mb-1 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FolderOpen className="h-4 w-4 text-orange-400" />
          <h3 className="text-sm font-bold text-white">Workspaces</h3>
        </div>
        <button onClick={() => { setEditing(null); setDialogOpen(true) }}
          className="flex h-8 items-center gap-1.5 rounded-lg border border-white/[0.1] bg-white/[0.04] px-3 text-xs font-medium text-zinc-300 transition-all hover:border-orange-500/30 hover:text-orange-400 active:scale-[0.97]">
          <Plus className="h-3.5 w-3.5" />New Workspace
        </button>
      </div>
      <p className="mb-5 text-xs text-zinc-600">Group projects by team, department, or matter type</p>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2].map((i) => <Skeleton key={i} className="h-14 rounded-xl bg-white/[0.04]" />)}
        </div>
      ) : !workspaces?.length ? (
        <div className="py-8 text-center animate-fade-in">
          <FolderOpen className="mx-auto mb-2 h-8 w-8 text-zinc-700 animate-pulse" />
          <p className="text-sm text-zinc-500">No workspaces yet</p>
          <p className="mt-1 text-xs text-zinc-700">Create one to organise projects by team or matter</p>
        </div>
      ) : (
        <div className="space-y-2">
          {workspaces.map((ws) => (
            <div key={ws.id}
              className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.03] p-3 transition-all duration-200 hover:border-orange-500/15 hover:bg-white/[0.05] hover:translate-x-0.5">
              <div>
                <p className="text-sm font-semibold text-white">{ws.name}</p>
                {ws.description && <p className="mt-0.5 text-xs text-zinc-600">{ws.description}</p>}
              </div>
              <button onClick={() => { setEditing(ws); setDialogOpen(true) }}
                className="flex h-7 w-7 items-center justify-center rounded-lg text-zinc-600 hover:bg-white/[0.06] hover:text-orange-400 active:scale-90 transition-all duration-200">
                <Pencil className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
      <WorkspaceDialog open={dialogOpen} onOpenChange={setDialogOpen} editing={editing} />
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const revealRef = useStaggerReveal(75)

  return (
    <div>
      <div className="animate-fade-up">
        <PageHeader
          title="Settings"
          description="Manage organisation preferences and workspaces"
        />
      </div>
      <div ref={revealRef} className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-4xl">
        <OrgSettingsCard />
        <WorkspacesCard />
      </div>
    </div>
  )
}
