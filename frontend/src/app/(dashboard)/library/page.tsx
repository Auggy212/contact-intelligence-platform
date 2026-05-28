"use client"

import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useLibrary, useLibrarySuggest, useCreateClause, useDeleteClause } from "@/lib/hooks/use-library"
import { PageHeader } from "@/components/shared/page-header"
import { EmptyState } from "@/components/shared/empty-state"
import { ConfirmDialog } from "@/components/shared/confirm-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { BookOpen, Plus, Trash2, Search, Sparkles, Loader2 } from "lucide-react"
import type { ClauseLibraryEntry } from "@/lib/types/api"
import { formatRelative, cn } from "@/lib/utils"
import { useStaggerReveal } from "@/hooks/use-scroll-reveal"

function useDebounce<T>(value: T, delay: number) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

const schema = z.object({
  title: z.string().min(1),
  body_text: z.string().min(1),
  category: z.string().optional(),
  tags: z.string().optional(),
})
type FormValues = z.infer<typeof schema>

function AddClauseDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const { mutateAsync, isPending } = useCreateClause()
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(v: FormValues) {
    await mutateAsync(v)
    reset()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg border-white/[0.08] bg-[#111111] text-white animate-scale-in">
        <DialogHeader><DialogTitle className="text-white">Add Clause</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label className="text-zinc-300">Title *</Label>
            <Input placeholder="e.g. Limitation of Liability" className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60" {...register("title")} />
            {errors.title && <p className="text-xs text-red-500">{errors.title.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label className="text-zinc-300">Clause Text *</Label>
            <Textarea rows={5} placeholder="Full clause language…" className="rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60 resize-none" {...register("body_text")} />
            {errors.body_text && <p className="text-xs text-red-500">{errors.body_text.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-zinc-300">Category</Label>
              <Input placeholder="e.g. Liability" className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60" {...register("category")} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-zinc-300">Tags</Label>
              <Input placeholder="comma-separated" className="h-11 rounded-xl border-white/[0.08] bg-[#1C1E26] text-white placeholder:text-zinc-600 focus:border-orange-500/60" {...register("tags")} />
            </div>
          </div>
          <DialogFooter className="gap-2">
            <button type="button" onClick={() => onOpenChange(false)}
              className="flex h-10 items-center rounded-xl border border-white/[0.1] bg-white/[0.04] px-4 text-sm font-medium text-zinc-300 hover:text-white transition-all hover:bg-white/[0.06] active:scale-[0.98]">
              Cancel
            </button>
            <button type="submit" disabled={isPending}
              className="flex h-10 items-center gap-2 rounded-xl bg-orange-500 px-4 text-sm font-bold text-white hover:bg-orange-400 active:scale-[0.98] disabled:opacity-50 hover:scale-[1.02]">
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {isPending ? "Adding…" : "Add Clause"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function ClauseCard({ clause, onDelete }: { clause: ClauseLibraryEntry; onDelete: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false)
  const tags = clause.tags?.split(",").map((t) => t.trim()).filter(Boolean) ?? []

  return (
    <Card className="hover:shadow-lg transition-all border-white/[0.07] bg-[#111111] hover:border-orange-500/25 duration-300 hover:shadow-orange-500/5 reveal">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-sm font-semibold leading-tight text-white">{clause.title}</CardTitle>
          <button className="flex h-6 w-6 items-center justify-center rounded-lg text-zinc-500 hover:bg-red-500/10 hover:text-red-400 transition-all duration-200 hover:scale-110" onClick={() => onDelete(clause.id)}>
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          {clause.category && (
            <span className="text-xs bg-orange-500/12 text-orange-400 border border-orange-500/20 px-2 py-0.5 rounded-full">{clause.category}</span>
          )}
          {tags.map((t) => (
            <span key={t} className="text-xs bg-zinc-800 text-zinc-400 border border-zinc-700 px-2 py-0.5 rounded-full">{t}</span>
          ))}
          <span className={cn("text-xs px-2 py-0.5 rounded-full border ml-auto capitalize", clause.status === "approved" ? "bg-emerald-500/12 text-emerald-400 border-emerald-500/20" : "bg-zinc-800 text-zinc-500 border-zinc-700")}>
            {clause.status}
          </span>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <p className={cn("text-xs text-zinc-400 leading-relaxed", !expanded && "line-clamp-3")}>
          {clause.body_text}
        </p>
        {clause.body_text.length > 200 && (
          <button onClick={() => setExpanded((v) => !v)} className="text-xs text-orange-400 hover:text-orange-300 font-medium transition-colors mt-1">
            {expanded ? "Show less" : "Show more"}
          </button>
        )}
        <p className="text-xs text-zinc-600 mt-2">{formatRelative(clause.created_at)}</p>
      </CardContent>
    </Card>
  )
}

export default function LibraryPage() {
  const { data: allClauses, isLoading } = useLibrary()
  const { mutate: deleteClause, isPending: deleting } = useDeleteClause()
  const [addOpen, setAddOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [searchInput, setSearchInput] = useState("")
  const debouncedSearch = useDebounce(searchInput, 400)

  const { data: searchResults, isFetching: searching } = useLibrarySuggest(debouncedSearch)

  const displayClauses = debouncedSearch.length >= 10 ? (searchResults ?? []) : (allClauses ?? [])
  const isSearchMode = debouncedSearch.length >= 10

  const revealRef = useStaggerReveal(50)

  return (
    <div>
      <div className="animate-fade-up">
        <PageHeader
          title="Clause Library"
          description="Approved clauses for your organisation — auto-populated when findings are approved"
          action={
            <button onClick={() => setAddOpen(true)}
              className="flex h-9 items-center gap-2 rounded-xl bg-orange-500 px-4 text-sm font-bold text-white shadow-lg shadow-orange-500/20 transition-all hover:bg-orange-400 hover:scale-[1.02] active:scale-[0.98] animate-glow-pulse">
              <Plus className="w-4 h-4 mr-2" />Add Clause
            </button>
          }
        />
      </div>

      <div className="relative mb-6 max-w-lg animate-fade-in delay-75">
        {searching ? (
          <Sparkles className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-orange-400 animate-pulse" />
        ) : (
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        )}
        <Input
          placeholder="Semantic search (min 10 characters)…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="pl-9 transition-all focus:ring-2 focus:ring-orange-500/10"
        />
        {isSearchMode && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-orange-400 font-semibold animate-pulse-slow">AI Search</span>
        )}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-40 rounded-lg" />)}
        </div>
      ) : displayClauses.length === 0 ? (
        <div className="animate-fade-in delay-100">
          <EmptyState
            icon={BookOpen}
            title={isSearchMode ? "No matching clauses found" : "Library is empty"}
            description={isSearchMode ? "Try different search terms" : "Clauses appear here when findings are approved in project reviews"}
            action={!isSearchMode ? { label: "Add Clause", onClick: () => setAddOpen(true) } : undefined}
          />
        </div>
      ) : (
        <div ref={revealRef} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {displayClauses.map((clause) => (
            <ClauseCard key={clause.id} clause={clause} onDelete={setDeleteId} />
          ))}
        </div>
      )}

      <AddClauseDialog open={addOpen} onOpenChange={setAddOpen} />
      <ConfirmDialog
        open={!!deleteId}
        onOpenChange={(v) => !v && setDeleteId(null)}
        title="Remove Clause"
        description="This clause will be removed from the library. This cannot be undone."
        confirmLabel="Remove"
        onConfirm={() => { if (deleteId) { deleteClause(deleteId); setDeleteId(null) } }}
        loading={deleting}
      />
    </div>
  )
}
