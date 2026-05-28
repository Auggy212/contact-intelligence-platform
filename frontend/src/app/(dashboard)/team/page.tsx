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
import { useStaggerReveal } from "@/hooks/use-scroll-reveal"
import type { Role } from "@/lib/types/api"

const roleConfig: Record<Role, { label: string; className: string }> = {
  admin:    { label: "Admin",    className: "bg-orange-500/12 text-orange-400 border-orange-500/20" },
  reviewer: { label: "Reviewer", className: "bg-blue-500/12 text-blue-400 border-blue-500/20" },
  viewer:   { label: "Viewer",   className: "bg-zinc-800 text-zinc-400 border-zinc-700" },
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
      <DialogContent className="max-w-sm border-white/[0.08] bg-[#111111] text-white animate-scale-in">
        <DialogHeader><DialogTitle className="text-white">Invite Team Member</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="mt-2 space-y-4">
          <div className="space-y-2">
            <Label className="text-sm font-medium text-zinc-300">Email <span className="text-orange-400">*</span></Label>
            <input type="email" placeholder="colleague@company.com"
              className="h-11 w-full rounded-xl border border-white/[0.08] bg-[#1C1E26] px-4 text-sm text-white placeholder-zinc-600 outline-none focus:border-orange-500/60 focus:ring-2 focus:ring-orange-500/15 transition-all duration-200"
              {...register("email")} />
            {errors.email && <p className="text-xs text-red-400">{errors.email.message}</p>}
          </div>
          <div className="space-y-2">
            <Label className="text-sm font-medium text-zinc-300">Role</Label>
            <Select defaultValue="viewer" onValueChange={(v) => setValue("role", v as Role)}>
              <SelectTrigger className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-zinc-300">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-white/[0.08] bg-[#1C1E26]">
                <SelectItem value="admin">Admin — full access</SelectItem>
                <SelectItem value="reviewer">Reviewer — can review findings</SelectItem>
                <SelectItem value="viewer">Viewer — read-only</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DialogFooter className="gap-2">
            <button type="button" onClick={() => onOpenChange(false)}
              className="flex h-10 items-center rounded-xl border border-white/[0.1] bg-white/[0.04] px-4 text-sm font-medium text-zinc-300 hover:text-white transition-all hover:bg-white/[0.06] active:scale-[0.98]">
              Cancel
            </button>
            <button type="submit" disabled={isPending}
              className="flex h-10 items-center gap-2 rounded-xl bg-orange-500 px-4 text-sm font-bold text-white hover:bg-orange-400 active:scale-[0.98] disabled:opacity-50 hover:scale-[1.02]">
              {isPending ? "Inviting…" : "Send Invite"}
            </button>
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

  const revealRef = useStaggerReveal<HTMLTableSectionElement>(45)

  return (
    <div>
      <div className="animate-fade-up">
        <PageHeader
          title="Team"
          description="Manage organisation members, roles, and access"
          action={
            <button onClick={() => setInviteOpen(true)}
              className="flex h-9 items-center gap-2 rounded-xl bg-orange-500 px-4 text-sm font-bold text-white shadow-lg shadow-orange-500/20 transition-all hover:bg-orange-400 hover:scale-[1.02] active:scale-[0.98] animate-glow-pulse">
              <Plus className="h-4 w-4" />Invite Member
            </button>
          }
        />
      </div>

      {isLoading ? (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}</div>
      ) : !members?.length ? (
        <div className="animate-fade-in delay-75">
          <EmptyState icon={Users} title="No team members" description="Invite colleagues to collaborate on contract reviews" action={{ label: "Invite Member", onClick: () => setInviteOpen(true) }} />
        </div>
      ) : (
        <div className="rounded-2xl border border-white/[0.07] bg-[#111111] overflow-hidden animate-scale-in delay-75 hover:border-white/[0.1] transition-all duration-300">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                <th className="px-5 py-3 text-left text-xs font-bold uppercase tracking-widest text-zinc-600">Member</th>
                <th className="px-5 py-3 text-left text-xs font-bold uppercase tracking-widest text-zinc-600">Role</th>
                <th className="hidden px-5 py-3 text-left text-xs font-bold uppercase tracking-widest text-zinc-600 md:table-cell">Joined</th>
                <th className="w-14 px-5 py-3" />
              </tr>
            </thead>
            <tbody ref={revealRef}>
              {members.map((m) => {
                const user = m.user
                const initials = user?.full_name?.split(" ").map((p) => p[0]).join("").toUpperCase().slice(0, 2) ?? "?"
                return (
                  <tr key={m.id} className="reveal border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] transition-all duration-200">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-orange-500/15 text-xs font-bold text-orange-400 transition-all hover:scale-105 duration-200">
                          {initials}
                        </div>
                        <div>
                          <p className="font-semibold text-white">{user?.full_name ?? "Pending"}</p>
                          <p className="text-xs text-zinc-600">{user?.email ?? "invite pending"}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <Select defaultValue={m.role} onValueChange={(v) => updateRole({ id: m.id, data: { role: v as Role } })}>
                        <SelectTrigger className="h-8 w-32 rounded-lg border-white/[0.08] bg-white/[0.04] text-xs text-zinc-300">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="border-white/[0.08] bg-[#1C1E26]">
                          {(["admin", "reviewer", "viewer"] as Role[]).map((r) => (
                            <SelectItem key={r} value={r} className="capitalize text-zinc-300">{roleConfig[r].label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="hidden px-5 py-3.5 text-xs text-zinc-600 md:table-cell">{formatDate(m.created_at)}</td>
                    <td className="px-5 py-3.5">
                      <button onClick={() => setRemoveId(m.id)}
                        className="flex h-7 w-7 items-center justify-center rounded-lg text-zinc-700 hover:bg-red-500/10 hover:text-red-400 transition-all duration-200 hover:scale-110 active:scale-90">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
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
