"""Organization repository for managing tenant boundary entities."""
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.organization import Organization
from backend.app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, session: AsyncSession):
        super().__init__(Organization, session)

    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Fetch organization by unique URL slug."""
        result = await self.session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_active(self, skip: int = 0, limit: int = 100) -> Sequence[Organization]:
        """List active organizations."""
        result = await self.session.execute(
            select(Organization)
            .where(Organization.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
