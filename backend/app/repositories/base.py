"""Base asynchronous repository with generic CRUD capabilities."""
from typing import Generic, TypeVar, Type, Optional, List, Any, Sequence
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository providing standardized async persistence operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: str) -> Optional[ModelType]:
        """Fetch a single entity by its primary key ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """List entities with pagination."""
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, entity: ModelType) -> ModelType:
        """Add and commit a new entity."""
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelType, values: Optional[dict] = None) -> ModelType:
        """Commit updates to an existing entity, optionally updating from values dict."""
        if values:
            for k, v in values.items():
                setattr(entity, k, v)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity_or_id: Any) -> bool:
        """Delete an entity by its ID or entity instance."""
        if isinstance(entity_or_id, str):
            entity = await self.get_by_id(entity_or_id)
        else:
            entity = entity_or_id
        if entity:
            await self.session.delete(entity)
            await self.session.commit()
            return True
        return False

