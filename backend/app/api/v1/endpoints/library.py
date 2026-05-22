import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_tenant_id, get_user_id
from app.schemas.library import ClauseLibraryCreate, ClauseLibraryOut, ClauseLibraryUpdate
from app.services.library_service import ClauseLibraryService

router = APIRouter(prefix="/clause-library", tags=["Clause Library"])


@router.get("", response_model=list[ClauseLibraryOut])
async def list_entries(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ClauseLibraryService(session, uuid.UUID(tenant_id))
    return await svc.list_all()


@router.post("", response_model=ClauseLibraryOut, status_code=201)
async def create_entry(
    data: ClauseLibraryCreate,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ClauseLibraryService(session, uuid.UUID(tenant_id))
    return await svc.create(data, uuid.UUID(user_id))


@router.get("/suggest", response_model=list[dict])
async def suggest_similar(
    q: str = Query(..., min_length=10, description="Clause text to find similar approved clauses for"),
    top_k: int = Query(5, ge=1, le=20),
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ClauseLibraryService(session, uuid.UUID(tenant_id))
    return await svc.search_similar(q, top_k=top_k)


@router.get("/search", response_model=list[dict], include_in_schema=False)
async def search_similar(
    q: str = Query(..., min_length=10),
    top_k: int = Query(5, ge=1, le=20),
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ClauseLibraryService(session, uuid.UUID(tenant_id))
    return await svc.search_similar(q, top_k=top_k)


@router.patch("/{entry_id}", response_model=ClauseLibraryOut)
async def update_entry(
    entry_id: uuid.UUID,
    data: ClauseLibraryUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ClauseLibraryService(session, uuid.UUID(tenant_id))
    return await svc.update(entry_id, data)


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = ClauseLibraryService(session, uuid.UUID(tenant_id))
    await svc.delete(entry_id)
