"""Security module: password hashing, JWT creation/validation, and claims management."""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
import jwt
from backend.app.core.config import settings
from backend.app.core.exceptions import AppException


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt with salt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hashed password."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    data: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
    subject: Optional[str] = None,
    claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a signed JWT access token containing subject and tenant claims."""
    to_encode: Dict[str, Any] = {}
    if data:
        to_encode.update(data)
    if claims:
        to_encode.update(claims)
    if subject:
        to_encode["sub"] = subject

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    })

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    data: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
    subject: Optional[str] = None,
) -> str:
    """Generate a signed JWT refresh token for session extension."""
    to_encode: Dict[str, Any] = {}
    if data:
        to_encode.update(data)
    if subject:
        to_encode["sub"] = subject

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "refresh",
    })

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )



def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AppException(
            message="Token has expired. Please authenticate again.",
            status_code=401,
            error_code="TOKEN_EXPIRED",
        )
    except jwt.InvalidTokenError:
        raise AppException(
            message="Invalid or malformed authentication token.",
            status_code=401,
            error_code="INVALID_TOKEN",
        )
