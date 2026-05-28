"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useRouter } from "next/navigation"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { useCreateProject } from "@/lib/hooks/use-projects"
import { Loader2, Plus } from "lucide-react"

const schema = z.object({
  name: z.string().min(1, "Name is required").max(200),
  description: z.string().max(500).optional(),
})
type FormValues = z.infer<typeof schema>

interface CreateProjectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreateProjectDialog({ open, onOpenChange }: CreateProjectDialogProps) {
  const router = useRouter()
  const { mutateAsync, isPending } = useCreateProject()
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(values: FormValues) {
    const project = await mutateAsync(values)
    reset()
    onOpenChange(false)
    router.push(`/projects/${project.id}/upload`)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md border-white/[0.08] bg-[#111111] text-white shadow-2xl">
        <DialogHeader>
          <DialogTitle className="text-lg font-bold text-white">New Project</DialogTitle>
          <p className="text-sm text-zinc-500">Create a contract review workspace for your team.</p>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-2 space-y-5">
          <div className="space-y-2">
            <Label htmlFor="proj-name" className="text-sm font-medium text-zinc-300">
              Project Name <span className="text-orange-400">*</span>
            </Label>
            <Input
              id="proj-name"
              placeholder="e.g. Vendor Agreement Q3 2026"
              className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60 focus:ring-orange-500/15"
              {...register("name")}
            />
            {errors.name && <p className="text-xs text-red-400">{errors.name.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="proj-desc" className="text-sm font-medium text-zinc-300">
              Description <span className="font-normal text-zinc-600">(optional)</span>
            </Label>
            <Textarea
              id="proj-desc"
              placeholder="Brief context about this contract review…"
              rows={3}
              className="rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60 focus:ring-orange-500/15 resize-none"
              {...register("description")}
            />
          </div>

          <DialogFooter className="gap-2 pt-1">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
              className="flex h-10 items-center justify-center rounded-xl border border-white/[0.1] bg-white/[0.04] px-5 text-sm font-medium text-zinc-300 transition-all hover:border-white/20 hover:text-white disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="flex h-10 items-center justify-center gap-2 rounded-xl bg-orange-500 px-5 text-sm font-bold text-white shadow-lg shadow-orange-500/20 transition-all hover:bg-orange-400 active:scale-[0.97] disabled:opacity-50"
            >
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              {isPending ? "Creating…" : "Create Project"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
