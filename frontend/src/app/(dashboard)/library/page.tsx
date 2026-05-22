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
import { BookOpen, Plus, Trash2, Search, Sparkles } from "lucide-react"
import type { ClauseLibraryEntry } from "@/lib/types/api"
import { formatRelative, cn } from "@/lib/utils"

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
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>Add Clause</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Title *</Label>
            <Input placeholder="e.g. Limitation of Liability" {...register("title")} />
            {errors.title && <p className="text-xs text-red-500">{errors.title.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label>Clause Text *</Label>
            <Textarea rows={5} placeholder="Full clause language…" {...register("body_text")} />
            {errors.body_text && <p className="text-xs text-red-500">{errors.body_text.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Category</Label>
              <Input placeholder="e.g. Liability" {...register("category")} />
            </div>
            <div className="space-y-1.5">
              <Label>Tags</Label>
              <Input placeholder="comma-separated" {...register("tags")} />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={isPending}>{isPending ? "Adding…" : "Add Clause"}</Button>
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
    <Card className="hover:shadow-sm transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-sm font-semibold leading-tight">{clause.title}</CardTitle>
          <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-slate-400 hover:text-red-500 shrink-0" onClick={() => onDelete(clause.id)}>
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          {clause.category && (
            <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">{clause.category}</span>
          )}
          {tags.map((t) => (
            <span key={t} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">{t}</span>
          ))}
          <span className={cn("text-xs px-2 py-0.5 rounded-full border ml-auto capitalize", clause.status === "approved" ? "bg-green-50 text-green-700 border-green-200" : "bg-slate-50 text-slate-500 border-slate-200")}>
            {clause.status}
          </span>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <p className={cn("text-xs text-slate-600 leading-relaxed", !expanded && "line-clamp-3")}>
          {clause.body_text}
        </p>
        {clause.body_text.length > 200 && (
          <button onClick={() => setExpanded((v) => !v)} className="text-xs text-blue-600 hover:underline mt-1">
            {expanded ? "Show less" : "Show more"}
          </button>
        )}
        <p className="text-xs text-slate-400 mt-2">{formatRelative(clause.created_at)}</p>
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

  return (
    <div>
      <PageHeader
        title="Clause Library"
        description="Approved clauses for your organisation — auto-populated when findings are approved"
        action={<Button onClick={() => setAddOpen(true)}><Plus className="w-4 h-4 mr-2" />Add Clause</Button>}
      />

      <div className="relative mb-6 max-w-lg">
        {searching ? (
          <Sparkles className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-blue-500 animate-pulse" />
        ) : (
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        )}
        <Input
          placeholder="Semantic search (min 10 characters)…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="pl-9"
        />
        {isSearchMode && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-blue-500 font-medium">AI Search</span>
        )}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-40 rounded-lg" />)}
        </div>
      ) : displayClauses.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title={isSearchMode ? "No matching clauses found" : "Library is empty"}
          description={isSearchMode ? "Try different search terms" : "Clauses appear here when findings are approved in project reviews"}
          action={!isSearchMode ? { label: "Add Clause", onClick: () => setAddOpen(true) } : undefined}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
