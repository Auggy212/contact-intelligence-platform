from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileRole(StrEnum):
    TEMPLATE = "A"       # Master template
    PROPOSED = "B"       # Proposed draft
    VENDOR_REPLY = "C"   # Vendor reply / redline


class TaskType(StrEnum):
    TEMPLATE_COMPARISON = "template_comparison"
    VENDOR_DIFF = "vendor_diff"
    LAW_VALIDATION = "law_validation"
    CHECKLIST_VALIDATION = "checklist_validation"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SubscriptionPlan(StrEnum):
    TRIAL = "trial"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"


class AuditAction(StrEnum):
    # Document actions
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_PARSED = "document_parsed"
    # Task actions
    TASK_QUEUED = "task_queued"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    # Review actions
    FINDING_APPROVED = "finding_approved"
    FINDING_REJECTED = "finding_rejected"
    # Admin actions
    MEMBER_INVITED = "member_invited"
    MEMBER_REMOVED = "member_removed"
    ROLE_CHANGED = "role_changed"
    # Billing
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELED = "subscription_canceled"
    PAYMENT_FAILED = "payment_failed"


# Subscription limits
PLAN_LIMITS: dict[str, dict] = {
    SubscriptionPlan.TRIAL: {
        "projects_per_month": 3,
        "documents_per_project": 3,
        "max_file_size_mb": 10,
    },
    SubscriptionPlan.STARTER: {
        "projects_per_month": 25,
        "documents_per_project": 10,
        "max_file_size_mb": 25,
    },
    SubscriptionPlan.PROFESSIONAL: {
        "projects_per_month": 100,
        "documents_per_project": 30,
        "max_file_size_mb": 50,
    },
    SubscriptionPlan.ENTERPRISE: {
        "projects_per_month": -1,   # unlimited
        "documents_per_project": -1,
        "max_file_size_mb": 100,
    },
}

# Vector embedding dimensions for voyage-law-2 (clause-level, legacy)
EMBEDDING_DIMENSIONS = 1024

# Chunk-level embedding dimensions (Phase 6). Default provider is NVIDIA
# nv-embedqa-e5-v5 = 1024. If you switch EMBEDDING_PROVIDER to one with a
# different dim (e.g. local bge-small = 384, openai = 1536) you must re-embed
# into a fresh collection; the vector column below is sized for the default.
CHUNK_EMBEDDING_DIMENSIONS = 1024

# Max clause text length for embedding (characters)
MAX_CLAUSE_LENGTH = 8000

# S3/MinIO tenant path prefix pattern: {tenant_id}/{project_id}/{file_role}_{filename}
STORAGE_KEY_PATTERN = "{tenant_id}/{project_id}/{file_role}_{filename}"
