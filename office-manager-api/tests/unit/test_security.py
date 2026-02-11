"""Unit tests for security functions."""
import pytest
from datetime import timedelta

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_get_password_hash_returns_hash(self):
        """Test that password hashing returns a bcrypt hash."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_get_password_hash_unique_per_call(self):
        """Test that each hash is unique (different salts)."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash."""
        password = "testpassword123"
        invalid_hash = "not-a-valid-hash"

        # Should return False, not raise an exception
        assert verify_password(password, invalid_hash) is False


class TestJWTTokens:
    """Tests for JWT token functions."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "user-123", "tenant_id": "tenant-456", "role": "admin"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """Test access token with custom expiry."""
        data = {"sub": "user-123"}
        expires = timedelta(hours=1)
        token = create_access_token(data, expires_delta=expires)

        assert token is not None

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "user-123"}
        token = create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)

    def test_decode_token_valid(self):
        """Test decoding a valid token."""
        data = {"sub": "user-123", "tenant_id": "tenant-456"}
        token = create_access_token(data)

        payload = decode_token(token)

        assert payload["sub"] == "user-123"
        assert payload["tenant_id"] == "tenant-456"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_token_invalid(self):
        """Test decoding an invalid token raises exception."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid-token")

        assert exc_info.value.status_code == 401

    def test_decode_token_expired(self):
        """Test decoding an expired token raises exception."""
        from fastapi import HTTPException

        data = {"sub": "user-123"}
        # Create token that's already expired
        token = create_access_token(data, expires_delta=timedelta(seconds=-10))

        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)

        assert exc_info.value.status_code == 401
