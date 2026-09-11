"""Unit tests for cryptographic security, password hashing, and JWT handling."""
import pytest
from datetime import timedelta
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.app.core.exceptions import AppException


def test_password_hashing_and_verification():
    """Verify bcrypt salt hashing and validation correctness."""
    raw_pass = "P@ssword2026!Secure"
    hashed = hash_password(raw_pass)

    assert hashed != raw_pass
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_access_token_creation_and_decoding():
    """Verify JWT access token contains subject and claims with expiration."""
    subject_id = "user-12345"
    claims = {"org_id": "org-999", "role": "admin"}
    token = create_access_token(subject=subject_id, claims=claims)

    decoded = decode_token(token)
    assert decoded["sub"] == subject_id
    assert decoded["org_id"] == "org-999"
    assert decoded["role"] == "admin"
    assert decoded["type"] == "access"
    assert "exp" in decoded


def test_refresh_token_type():
    """Verify refresh tokens have distinct type 'refresh'."""
    token = create_refresh_token(subject="user-12345")
    decoded = decode_token(token)
    assert decoded["sub"] == "user-12345"
    assert decoded["type"] == "refresh"


def test_expired_token_raises_app_exception():
    """Verify expired token generates TOKEN_EXPIRED AppException with status 401."""
    expired_token = create_access_token(
        subject="user-12345",
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(AppException) as exc_info:
        decode_token(expired_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.error_code == "TOKEN_EXPIRED"


def test_tampered_token_raises_app_exception():
    """Verify corrupted or tampered token fails signature verification."""
    valid_token = create_access_token(subject="user-12345")
    tampered_token = valid_token[:-4] + "abcd"

    with pytest.raises(AppException) as exc_info:
        decode_token(tampered_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.error_code == "INVALID_TOKEN"
