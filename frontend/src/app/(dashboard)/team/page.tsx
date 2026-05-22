"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useTeam, useInviteMember, useUpdateMemberRole, useRemoveMember } from "@/lib/hooks/use-team"
import { PageHeader } from "@/components/shared/page-header"
import { EmptyState } from "@/components/shared/empty-state"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { Users, Plus, Trash2 } from "lucide-react"
import { formatDate } from "@/lib/utils"
import type { Role } from "@/lib/types/api"

const roleConfig: Record<Role, { label: string; className: string }> = {
  admin: { label: "Admin", className: "bg-purple-100 text-purple-700 border-purple-300" },
  reviewer: { label: "Reviewer", className: "bg-blue-100 text-blue-700 border-blue-300" },
  viewer: { label: "Viewer", className: "bg-slate-100 text-slate-600 border-slate-300" },
}

const inviteSchema = z.object({
  email: z.string().email(),
  role: z.enum(["admin", "reviewer", "viewer"]).default("viewer"),
})
type InviteForm = z.infer<typeof inviteSchema>

function InviteDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const { mutateAsync, isPending } = useInviteMember()
  const { register, handleSubmit, reset, setValue, formState: { errors } } = useForm<InviteForm>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(inviteSchema) as any, defaultValues: { role: "viewer" },
  })

  async function onSubmit(v: InviteForm) {
    await mutateAsync(v)
    reset()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle>Invite Team Member</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Email *</Label>
            <Input type="email" placeholder="colleague@company.com" {...register("email")} />
            {errors.email && <p className="text-xs text-red-500">{errors.email.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label>Role</Label>
            <Select defaultValue="viewer" onValueChange={(v) => setValue("role", v as Role)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin — full access</SelectItem>
                <SelectItem value="reviewer">Reviewer — can review findings</SelectItem>
                <SelectItem value="viewer">Viewer — read-only</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={isPending}>{isPending ? "Inviting…" : "Send Invite"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default function TeamPage() {
  const { data: members, isLoading } = useTeam()
  const { mutate: updateRole } = useUpdateMemberRole()
  const { mutate: removeMember, isPending: removing } = useRemoveMember()
  const [inviteOpen, setInviteOpen] = useState(false)
  const [removeId, setRemoveId] = useState<string | null>(null)

  return (
    <div>
      <PageHeader
        title="Team"
        description="Manage organisation members, roles, and access"
        action={<Button onClick={() => setInviteOpen(true)}><Plus className="w-4 h-4 mr-2" />Invite Member</Button>}
      />

      {isLoading ? (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}</div>
      ) : !members?.length ? (
        <EmptyState icon={Users} title="No team members" description="Invite colleagues to collaborate on contract reviews" action={{ label: "Invite Member", onClick: () => setInviteOpen(true) }} />
      ) : (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Member</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Role</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Joined</th>
                <th className="px-4 py-3 w-16" />
              </tr>
            </thead>
            <tbody>
              {members.map((m) => {
                const user = m.user
                const initials = user?.full_name?.split(" ").map((p) => p[0]).join("").toUpperCase().slice(0, 2) ?? "?"
                return (
                  <tr key={m.id} className="border-b last:border-0 hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <Avatar className="h-8 w-8">
                          {user?.avatar_url && <AvatarImage src={user.avatar_url} />}
                          <AvatarFallback className="text-xs">{initials}</AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-medium text-slate-900">{user?.full_name ?? "Pending"}</p>
                          <p className="text-xs text-slate-500">{user?.email ?? "invite pending"}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Select
                        defaultValue={m.role}
                        onValueChange={(v) => updateRole({ id: m.id, data: { role: v as Role } })}
                      >
                        <SelectTrigger className="w-32 h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {(["admin", "reviewer", "viewer"] as Role[]).map((r) => (
                            <SelectItem key={r} value={r} className="capitalize">{roleConfig[r].label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500 hidden md:table-cell">{formatDate(m.created_at)}</td>
                    <td className="px-4 py-3">
                      <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-slate-400 hover:text-red-500" onClick={() => setRemoveId(m.id)}>
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <InviteDialog open={inviteOpen} onOpenChange={setInviteOpen} />
      <ConfirmDialog
        open={!!removeId}
        onOpenChange={(v) => !v && setRemoveId(null)}
        title="Remove Member"
        description="This person will lose access to the organisation immediately."
        confirmLabel="Remove"
        onConfirm={() => { if (removeId) { removeMember(removeId); setRemoveId(null) } }}
        loading={removing}
      />
    </div>
  )
}
