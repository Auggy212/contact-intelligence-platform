"use client"

import { useParams } from "next/navigation"
import { DocumentVerifyView } from "@/components/verify/document-verify-view"

export default function VerifyPage() {
  const { projectId } = useParams<{ projectId: string }>()
  return <DocumentVerifyView projectId={projectId} />
}
