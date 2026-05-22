// ── Enums ────────────────────────────────────────────────────────────────────

export type ProjectStatus = "draft" | "processing" | "completed" | "failed"
export type FileRole = "A" | "B" | "C"
export type TaskType =
  | "template_comparison"
  | "vendor_diff"
  | "law_validation"
  | "checklist_validation"
export type TaskStatus = "queued" | "running" | "completed" | "failed"
export type Severity = "critical" | "high" | "medium" | "low" | "info"
export type ReviewerStatus = "pending" | "approved" | "rejected"
export type SubscriptionPlan = "trial" | "starter" | "professional" | "enterprise"
export type SubscriptionStatus = "active" | "past_due" | "canceled" | "trialing"
export type Role = "admin" | "reviewer" | "viewer"
export type FlagType =
  | "missing_clause"
  | "weakened_clause"
  | "modified"
  | "deleted"
  | "added"
  | "law_violation"
  | "law_at_risk"
  | "checklist_fail"
  | "checklist_not_found"

// ── Base ─────────────────────────────────────────────────────────────────────

export interface BaseEntity {
  id: string
  created_at: string
  updated_at: string
}

// ── Projects ─────────────────────────────────────────────────────────────────

export interface Project extends BaseEntity {
  organization_id: string
  workspace_id: string | null
  name: string
  description: string | null
  status: ProjectStatus
}

export interface ProjectCreate {
  name: string
  description?: string
  workspace_id?: string
}

export interface ProjectUpdate {
  name?: string
  description?: string
  status?: ProjectStatus
}

// ── Documents ────────────────────────────────────────────────────────────────

export interface ProjectFile extends BaseEntity {
  project_id: string
  file_role: FileRole
  original_filename: string
  file_size_bytes: number
  mime_type: string
  parse_status: string
}

export interface DocumentUploadResponse {
  file_id: string
  storage_key: string
  parse_status: string
  presigned_url: string | null
}

// ── Tasks ────────────────────────────────────────────────────────────────────

export interface AnalysisTask extends BaseEntity {
  project_id: string
  task_type: TaskType
  status: TaskStatus
  model_version: string | null
  prompt_version: string | null
  error_message: string | null
  celery_task_id: string | null
}

export interface TaskTriggerRequest {
  task_types: TaskType[]
}

// ── Findings ─────────────────────────────────────────────────────────────────

export interface ClauseFlag extends BaseEntity {
  clause_id: string
  task_id: string
  project_id: string
  flag_type: FlagType
  severity: Severity
  title: string
  description: string
  recommendation: string | null
  source_clause_id: string | null
  confidence: number | null
  reasoning_trace: string | null
  risk_score: number | null
  law_act_name: string | null
  law_section_number: string | null
  law_retrieved_text: string | null
  law_jurisdiction: string | null
  reviewer_status: ReviewerStatus
  reviewer_note: string | null
}

export interface ReviewFlagRequest {
  status: "approved" | "rejected"
  note?: string
}

// ── Checklist ────────────────────────────────────────────────────────────────

export interface ChecklistRule extends BaseEntity {
  organization_id: string
  created_by_user_id: string | null
  rule_code: string
  name: string
  description: string | null
  severity: Severity
  rule_config: Record<string, unknown>
  is_enabled: boolean
  is_default: boolean
}

export interface ChecklistRuleCreate {
  rule_code: string
  name: string
  description?: string
  severity: Severity
  rule_config: Record<string, unknown>
  is_enabled?: boolean
}

export interface ChecklistRuleUpdate {
  name?: string
  description?: string
  severity?: Severity
  rule_config?: Record<string, unknown>
  is_enabled?: boolean
}

// ── Clause Library ────────────────────────────────────────────────────────────

export interface ClauseLibraryEntry extends BaseEntity {
  organization_id: string
  title: string
  body_text: string
  category: string | null
  tags: string | null
  status: string
  is_active: boolean
}

export interface ClauseLibraryCreate {
  title: string
  body_text: string
  category?: string
  tags?: string
  status?: string
}

export interface ClauseLibraryUpdate {
  title?: string
  body_text?: string
  category?: string
  tags?: string
  status?: string
  is_active?: boolean
}

// ── Users / Team ─────────────────────────────────────────────────────────────

export interface User extends BaseEntity {
  clerk_user_id: string
  email: string
  full_name: string
  avatar_url: string | null
  is_active: boolean
}

export interface Membership extends BaseEntity {
  user_id: string
  organization_id: string
  role: Role
  is_active: boolean
  user: User | null
}

export interface InviteMemberRequest {
  email: string
  role?: Role
}

export interface UpdateMemberRoleRequest {
  role: Role
}

// ── Billing ──────────────────────────────────────────────────────────────────

export interface Subscription extends BaseEntity {
  organization_id: string
  stripe_customer_id: string | null
  stripe_subscription_id: string | null
  plan: SubscriptionPlan
  status: SubscriptionStatus
  current_period_start: string | null
  current_period_end: string | null
  trial_end: string | null
}

export interface UsageRecord extends BaseEntity {
  organization_id: string
  billing_period: string
  contracts_processed: number
  ai_tokens_used: number
  storage_bytes_used: number
}

export interface CreateCheckoutSessionRequest {
  plan: SubscriptionPlan
  success_url: string
  cancel_url: string
}

export interface CreateCheckoutSessionResponse {
  checkout_url: string
}

export interface CreatePortalSessionResponse {
  portal_url: string
}

// ── Organizations ─────────────────────────────────────────────────────────────

export interface Organization extends BaseEntity {
  clerk_org_id: string
  name: string
  slug: string
  logo_url: string | null
  is_active: boolean
}

export interface OrganizationUpdate {
  name?: string
  logo_url?: string
}

export interface Workspace extends BaseEntity {
  organization_id: string
  name: string
  description: string | null
  is_active: boolean
}

export interface WorkspaceCreate {
  name: string
  description?: string
}

export interface WorkspaceUpdate {
  name?: string
  description?: string
}

// ── Audit Log ─────────────────────────────────────────────────────────────────

export interface AuditLog extends BaseEntity {
  organization_id: string
  user_id: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  extra_data: Record<string, unknown> | null
  model_version: string | null
  prompt_version: string | null
  ip_address: string | null
}

// ── Plan limits ───────────────────────────────────────────────────────────────

export const PLAN_LIMITS: Record<SubscriptionPlan, { contracts: number | null; label: string; price: string }> = {
  trial: { contracts: 3, label: "Trial", price: "Free" },
  starter: { contracts: 25, label: "Starter", price: "₹4,999/mo" },
  professional: { contracts: 100, label: "Professional", price: "₹19,999/mo" },
  enterprise: { contracts: null, label: "Enterprise", price: "Custom" },
}

export const FILE_ROLE_LABELS: Record<FileRole, { label: string; description: string; color: string }> = {
  A: {
    label: "Master Template",
    description: "Your organisation's gold-standard baseline agreement",
    color: "blue",
  },
  B: {
    label: "Proposed Draft",
    description: "The client's customized version sent to vendor",
    color: "green",
  },
  C: {
    label: "Vendor Reply",
    description: "The vendor's counter-proposal with tracked changes",
    color: "orange",
  },
}

export const TASK_TYPE_LABELS: Record<TaskType, { label: string; description: string }> = {
  template_comparison: {
    label: "Template Comparison",
    description: "A vs B — find missing or weakened clauses",
  },
  vendor_diff: {
    label: "Vendor Diff Analysis",
    description: "B vs C — classify vendor modifications and assess risk",
  },
  law_validation: {
    label: "Indian Law Validation",
    description: "Validate against 6 Indian statutes via RAG",
  },
  checklist_validation: {
    label: "Checklist Validation",
    description: "Run business rules against extracted contract values",
  },
}

export const SEVERITY_CONFIG: Record<Severity, { label: string; color: string; bg: string; border: string; dot: string }> = {
  critical: { label: "Critical", color: "text-red-700", bg: "bg-red-50", border: "border-red-200", dot: "bg-red-500" },
  high: { label: "High", color: "text-orange-700", bg: "bg-orange-50", border: "border-orange-200", dot: "bg-orange-500" },
  medium: { label: "Medium", color: "text-yellow-700", bg: "bg-yellow-50", border: "border-yellow-200", dot: "bg-yellow-500" },
  low: { label: "Low", color: "text-blue-700", bg: "bg-blue-50", border: "border-blue-200", dot: "bg-blue-400" },
  info: { label: "Info", color: "text-gray-600", bg: "bg-gray-50", border: "border-gray-200", dot: "bg-gray-400" },
}
