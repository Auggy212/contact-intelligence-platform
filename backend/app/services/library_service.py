import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.integrations import qdrant_client
from app.integrations.voyage_client import embed_texts
from app.models.library import ClauseLibraryEntry
from app.schemas.library import ClauseLibraryCreate, ClauseLibraryUpdate


class ClauseLibraryService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._db = db
        self._tenant_id = tenant_id

    def _collection(self) -> str:
        return qdrant_client.tenant_collection_name(str(self._tenant_id))

    async def create(self, data: ClauseLibraryCreate, user_id: uuid.UUID) -> ClauseLibraryEntry:
        entry = ClauseLibraryEntry(
            organization_id=self._tenant_id,
            added_by_user_id=user_id,
            title=data.title,
            body_text=data.body_text,
            category=data.category,
            tags=data.tags,
            status=data.status,
        )
        self._db.add(entry)
        await self._db.flush()

        # Index in Qdrant
        embeddings = await embed_texts([data.body_text])
        point_id = str(entry.id)
        await qdrant_client.upsert_vectors(
            self._collection(),
            [{
                "id": point_id,
                "vector": embeddings[0],
                "payload": {
                    "title": data.title,
                    "status": data.status,
                    "category": data.category,
                    "tenant_id": str(self._tenant_id),
                },
            }],
        )
        entry.qdrant_point_id = point_id
        await self._db.flush()
        return entry

    async def search_similar(self, query_text: str, top_k: int = 5) -> list[dict]:
        from app.integrations.voyage_client import embed_query
        vector = await embed_query(query_text)
        return await qdrant_client.search_vectors(self._collection(), vector, top_k=top_k)

    async def list_all(self) -> list[ClauseLibraryEntry]:
        result = await self._db.execute(
            select(ClauseLibraryEntry).where(
                ClauseLibraryEntry.organization_id == self._tenant_id,
                ClauseLibraryEntry.is_active.is_(True),
            ).order_by(ClauseLibraryEntry.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, entry_id: uuid.UUID) -> ClauseLibraryEntry:
        result = await self._db.execute(
            select(ClauseLibraryEntry).where(
                ClauseLibraryEntry.id == entry_id,
                ClauseLibraryEntry.organization_id == self._tenant_id,
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise NotFoundError("Clause library entry not found")
        return entry

    async def update(self, entry_id: uuid.UUID, data: ClauseLibraryUpdate) -> ClauseLibraryEntry:
        entry = await self.get_by_id(entry_id)
        if data.title is not None:
            entry.title = data.title
        if data.body_text is not None:
            entry.body_text = data.body_text
        if data.category is not None:
            entry.category = data.category
        if data.tags is not None:
            entry.tags = data.tags
        if data.status is not None:
            entry.status = data.status
        if data.is_active is not None:
            entry.is_active = data.is_active
        await self._db.flush()
        return entry

    async def delete(self, entry_id: uuid.UUID) -> None:
        entry = await self.get_by_id(entry_id)
        if entry.qdrant_point_id:
            await qdrant_client.delete_vector(self._collection(), entry.qdrant_point_id)
        await self._db.delete(entry)
        await self._db.flush()
