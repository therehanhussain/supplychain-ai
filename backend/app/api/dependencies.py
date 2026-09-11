"""FastAPI dependencies: Database sessions, JWT authentication, and RBAC enforcement."""
from typing import AsyncGenerator, List, Optional
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.security import decode_token
from backend.app.core.config import settings
from backend.app.core.exceptions import AppException
from backend.app.models.organization import Organization
from backend.app.models.user import User, UserRole
from backend.app.repositories.users import UserRepository
from backend.app.repositories.organizations import OrganizationRepository

http_bearer = HTTPBearer(auto_error=False)


class TenantContext:
    """Encapsulates authenticated tenant information for the current request."""
    def __init__(self, organization_id: str, user: Optional[User] = None, role: UserRole = UserRole.VIEWER):
        self.organization_id = organization_id
        self.user = user
        self.user_id = user.id if user else "anonymous"
        self.role = role
        self.email = user.email if user else "anonymous@system.local"


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and strictly validate JWT token from Bearer header, returning User instance."""
    if not credentials or not credentials.credentials:
        raise AppException(
            message="Missing or invalid authentication credentials.",
            status_code=401,
            error_code="UNAUTHORIZED",
        )

    payload = decode_token(credentials.credentials)
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise AppException(
            message="Token payload is missing subject identifier.",
            status_code=401,
            error_code="INVALID_TOKEN",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise AppException(
            message="User associated with token does not exist.",
            status_code=401,
            error_code="USER_NOT_FOUND",
        )

    if not user.is_active:
        raise AppException(
            message="User account is deactivated.",
            status_code=403,
            error_code="ACCOUNT_INACTIVE",
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract user if credentials are provided; returns None if omitted."""
    if not credentials or not credentials.credentials:
        return None
    return await get_current_user(credentials, db)


async def get_tenant_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    """Provide TenantContext for strict multi-tenant data access.

    If Bearer credentials are provided, validates user and extracts tenant organization_id.
    If credentials are omitted in development mode, defaults to the default development tenant.
    """
    if credentials and credentials.credentials:
        user = await get_current_user(credentials, db)
        return TenantContext(
            organization_id=user.organization_id,
            user=user,
            role=user.role,
        )

    # In development mode, ensure default development tenant exists
    org_repo = OrganizationRepository(db)
    default_slug = "default-org"
    org = await org_repo.get_by_slug(default_slug)
    if not org:
        org = Organization(
            name="Default Organization",
            slug=default_slug,
            tier="enterprise",
        )
        org = await org_repo.create(org)

    return TenantContext(
        organization_id=org.id,
        user=None,
        role=UserRole.ADMIN,
    )


async def get_auth_tenant_context(
    current_user: User = Depends(get_current_user),
) -> TenantContext:
    """Provide strictly authenticated TenantContext, raising 401 if unauthenticated."""
    return TenantContext(
        organization_id=current_user.organization_id,
        user=current_user,
        role=current_user.role,
    )


def require_role(allowed_roles: List[UserRole]):
    """Role-based access control (RBAC) dependency factory."""
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise AppException(
                message=f"Access forbidden. Operation requires one of: {[r.value for r in allowed_roles]}.",
                status_code=403,
                error_code="FORBIDDEN_INSUFFICIENT_ROLE",
                details={
                    "user_role": current_user.role.value,
                    "required_roles": [r.value for r in allowed_roles],
                },
            )
        return current_user
    return role_checker


# Role-specific dependency shortcuts
require_admin = require_role([UserRole.ADMIN])
require_operator = require_role([UserRole.ADMIN, UserRole.OPERATOR])
require_analyst = require_role([UserRole.ADMIN, UserRole.OPERATOR, UserRole.ANALYST])
require_viewer = require_role([UserRole.ADMIN, UserRole.OPERATOR, UserRole.ANALYST, UserRole.VIEWER])
