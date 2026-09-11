"""Authentication router for registration, login, token refresh, and profile inspection."""
import re
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.exceptions import AppException
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.app.api.dependencies import get_current_user
from backend.app.models.organization import Organization
from backend.app.models.user import User, UserRole
from backend.app.repositories.organizations import OrganizationRepository
from backend.app.repositories.users import UserRepository
from backend.app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserProfileResponse,
    AuthResponse,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


def slugify(text: str) -> str:
    """Convert text to a lowercase URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)[:50]


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organization and initial administrator account",
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    org_repo = OrganizationRepository(db)

    # Check if user already exists
    existing_user = await user_repo.get_by_email(request.email)
    if existing_user:
        raise AppException(
            message=f"User with email '{request.email}' already exists.",
            status_code=409,
            error_code="EMAIL_ALREADY_EXISTS",
        )

    # Check or create organization
    org_slug = slugify(request.organization_name)
    existing_org = await org_repo.get_by_slug(org_slug)
    if not existing_org:
        organization = Organization(
            name=request.organization_name,
            slug=org_slug,
            tier="enterprise",
        )
        organization = await org_repo.create(organization)
    else:
        organization = existing_org

    # Create new user
    hashed = hash_password(request.password)
    user = User(
        organization_id=organization.id,
        email=request.email.lower().strip(),
        hashed_password=hashed,
        full_name=request.full_name,
        role=request.role or UserRole.ADMIN,
        is_active=True,
    )
    user = await user_repo.create(user)

    token_data = {
        "sub": user.id,
        "org_id": user.organization_id,
        "role": user.role.value,
        "email": user.email,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    user_profile = UserProfileResponse(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
        user=user_profile,
    )



@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email and password to receive JWT credentials",
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(request.email)

    if not user or not verify_password(request.password, user.hashed_password):
        raise AppException(
            message="Invalid email or password.",
            status_code=401,
            error_code="INVALID_CREDENTIALS",
        )

    if not user.is_active:
        raise AppException(
            message="Account has been suspended.",
            status_code=403,
            error_code="ACCOUNT_INACTIVE",
        )

    token_data = {
        "sub": user.id,
        "org_id": user.organization_id,
        "role": user.role.value,
        "email": user.email,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange valid refresh token for a new access token",
)
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(request.refresh_token)
    if payload.get("type") != "refresh":
        raise AppException(
            message="Token provided is not a valid refresh token.",
            status_code=400,
            error_code="INVALID_TOKEN_TYPE",
        )

    user_id = payload.get("sub")
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise AppException(
            message="User session is no longer active.",
            status_code=401,
            error_code="SESSION_INVALID",
        )

    token_data = {
        "sub": user.id,
        "org_id": user.organization_id,
        "role": user.role.value,
        "email": user.email,
    }
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=new_refresh_token,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get profile and role of currently authenticated user",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return UserProfileResponse(
        id=current_user.id,
        organization_id=current_user.organization_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
    )
