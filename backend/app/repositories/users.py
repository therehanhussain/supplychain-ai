"""User repository with organization scoping and authentication lookups."""
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.user import User, UserRole
from backend.app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by case-insensitive unique email."""
        result = await self.session.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_org(self, user_id: str, organization_id: str) -> Optional[User]:
        """Fetch user scoped strictly to organization (tenant isolation)."""
        result = await self.session.execute(
            select(User).where(
                User.id == user_id,
                User.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self, organization_id: str, skip: int = 0, limit: int = 100
    ) -> Sequence[User]:
        """List users belonging to an organization."""
        result = await self.session.execute(
            select(User)
            .where(User.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
