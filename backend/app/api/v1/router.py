from fastapi import APIRouter

from app.api.v1.endpoints import (
    audit,
    billing,
    checklist,
    debug,
    documents,
    export,
    health,
    library,
    organizations,
    projects,
    search,
    tasks,
    transparency,
    users,
    webhooks,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(debug.router)
api_router.include_router(organizations.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(documents.router)
api_router.include_router(search.router)
api_router.include_router(tasks.router)
api_router.include_router(checklist.router)
api_router.include_router(transparency.router)
api_router.include_router(library.router)
api_router.include_router(audit.router)
api_router.include_router(billing.router)
api_router.include_router(webhooks.router)
api_router.include_router(export.router)
