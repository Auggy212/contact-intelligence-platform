"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useOrganization } from "@/lib/hooks/use-organization"
import { useWorkspaces, useCreateWorkspace, useUpdateWorkspace } from "@/lib/hooks/use-organization"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { Building2, Plus, Pencil, FolderOpen, Globe, Save, Loader2 } from "lucide-react"
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
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-slate-500" />
          <CardTitle className="text-base">Organisation Settings</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1.5">
              <Label>Organisation Name *</Label>
              <Input placeholder="Acme Legal LLP" {...register("name")} />
              {errors.name && <p className="text-xs text-red-500">{errors.name.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Logo URL</Label>
              <Input placeholder="https://cdn.example.com/logo.png" {...register("logo_url")} />
              {errors.logo_url && <p className="text-xs text-red-500">{errors.logo_url.message}</p>}
              <p className="text-xs text-slate-400">Paste a public URL to your organisation&apos;s logo image</p>
            </div>
            {org?.slug && (
              <div className="space-y-1.5">
                <Label>Organisation Slug</Label>
                <div className="flex items-center gap-2 h-9 px-3 rounded-md border bg-slate-50 text-sm text-slate-500">
                  <Globe className="w-3.5 h-3.5 shrink-0" />
                  <span className="font-mono">{org.slug}</span>
                </div>
                <p className="text-xs text-slate-400">Slug is set by Clerk and cannot be changed here</p>
              </div>
            )}
            <div className="flex justify-end pt-2">
              <Button type="submit" size="sm" disabled={!isDirty || updating}>
                {updating ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving…</>
                ) : (
                  <><Save className="w-4 h-4 mr-2" />Save Changes</>
                )}
              </Button>
            </div>
          </form>
        )}
      </CardContent>
    </Card>
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
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit Workspace" : "New Workspace"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Name *</Label>
            <Input placeholder="e.g. Mumbai Office" {...register("name")} />
            {errors.name && <p className="text-xs text-red-500">{errors.name.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Textarea rows={2} placeholder="Optional description" {...register("description")} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Saving…" : editing ? "Save Changes" : "Create"}
            </Button>
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
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-slate-500" />
            <CardTitle className="text-base">Workspaces</CardTitle>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => { setEditing(null); setDialogOpen(true) }}
          >
            <Plus className="w-4 h-4 mr-1.5" />New Workspace
          </Button>
        </div>
        <p className="text-sm text-slate-500">Group projects by team, department, or matter type</p>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2].map((i) => <Skeleton key={i} className="h-14 rounded-lg" />)}
          </div>
        ) : !workspaces?.length ? (
          <div className="text-center py-8">
            <FolderOpen className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">No workspaces yet</p>
            <p className="text-xs text-slate-400 mt-1">Create one to organise projects by team or matter</p>
          </div>
        ) : (
          <div className="space-y-2">
            {workspaces.map((ws) => (
              <div
                key={ws.id}
                className="flex items-center justify-between p-3 rounded-lg border hover:bg-slate-50 transition-colors"
              >
                <div>
                  <p className="text-sm font-medium text-slate-900">{ws.name}</p>
                  {ws.description && (
                    <p className="text-xs text-slate-500 mt-0.5">{ws.description}</p>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 w-7 p-0 text-slate-400 hover:text-slate-700"
                  onClick={() => { setEditing(ws); setDialogOpen(true) }}
                >
                  <Pencil className="w-3.5 h-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
      <WorkspaceDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editing={editing}
      />
    </Card>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  return (
    <div>
      <PageHeader
        title="Settings"
        description="Manage organisation preferences and workspaces"
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-4xl">
        <OrgSettingsCard />
        <WorkspacesCard />
      </div>
    </div>
  )
}
