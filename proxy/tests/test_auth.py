"""
Tests for authentication API endpoints.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from jose import jwt

from app.api.v1.auth import (
    create_access_token,
    create_refresh_token,
    generate_api_key,
    get_current_user_id,
    router,
)
from app.config import get_settings

settings = get_settings()


# Sync tests for simple utility functions
class TestTokenGeneration:
    """Tests for JWT token generation."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id)

        # Decode and verify
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = str(uuid.uuid4())
        token = create_refresh_token(user_id)

        # Decode and verify
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_access_token_expiration(self):
        """Test that access token has correct expiration."""
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id)

        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

        exp = datetime.fromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

        # Allow 10 second tolerance
        assert abs((exp - expected_exp).total_seconds()) < 10


class TestApiKeyGeneration:
    """Tests for API key generation."""

    def test_generate_api_key_format(self):
        """Test API key format."""
        full_key, key_hash, key_prefix = generate_api_key()

        assert full_key.startswith("acc_")
        assert len(full_key) == 56  # "acc_" (4) + 24*2 hex chars (48) + underscore = 52+4
        assert key_prefix == full_key[:12]
        assert key_prefix.startswith("acc_")

    def test_generate_api_key_unique(self):
        """Test that generated keys are unique."""
        keys = [generate_api_key()[0] for _ in range(10)]

        assert len(set(keys)) == 10  # All unique

    def test_generate_api_key_hash(self):
        """Test that key hash is generated."""
        full_key, key_hash, key_prefix = generate_api_key()

        assert key_hash != full_key
        assert len(key_hash) > 0


# Async tests for auth endpoints
@pytest.mark.asyncio
class TestAuthEndpoints:
    """Tests for authentication API endpoints."""

    async def test_register_success(self, async_client: AsyncClient, mock_db):
        """Test successful user registration."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "SecurePass123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["plan"] == "free"
        assert data["is_active"] is True

    async def test_register_duplicate_email(self, async_client: AsyncClient, mock_db):
        """Test registration with duplicate email fails."""
        # First registration
        await async_client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "SecurePass123!"},
        )

        # Second registration with same email
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "DifferentPass456!"},
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    async def test_login_success(self, async_client: AsyncClient, mock_user):
        """Test successful login."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "SecurePass123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, async_client: AsyncClient, mock_db):
        """Test login with invalid credentials."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "WrongPass!"},
        )

        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()

    async def test_get_current_user_authenticated(self, async_client: AsyncClient, auth_headers):
        """Test getting current user with valid auth."""
        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data

    async def test_get_current_user_unauthenticated(self, async_client: AsyncClient):
        """Test getting current user without auth fails."""
        response = await async_client.get("/api/v1/auth/me")

        assert response.status_code == 401

    async def test_create_api_key_authenticated(self, async_client: AsyncClient, auth_headers):
        """Test API key creation with auth."""
        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test Key"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "key" in data
        assert data["key"].startswith("acc_")
        assert "warning" in data

    async def test_list_api_keys_authenticated(self, async_client: AsyncClient, auth_headers):
        """Test listing API keys with auth."""
        # Create a key first
        await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test Key"},
            headers=auth_headers,
        )

        # List keys
        response = await async_client.get("/api/v1/auth/api-keys", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert "key_prefix" in data[0]
        assert "key" not in data[0]  # Full key should not be returned

    async def test_revoke_api_key(self, async_client: AsyncClient, auth_headers):
        """Test revoking an API key."""
        # Create a key
        create_response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test Key"},
            headers=auth_headers,
        )
        key_id = create_response.json()["id"]

        # Revoke the key
        response = await async_client.delete(
            f"/api/v1/auth/api-keys/{key_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "revoked"


# Fixtures
@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    return app


@pytest.fixture
def async_client(app):
    """Create async test client."""
    from httpx import AsyncClient

    return AsyncClient(app=app, base_url="http://test")


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_user():
    """Mock user for testing."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.is_active = True
    user.plan.value = "free"
    user.hashed_password = "$2b$12$..."  # Mock bcrypt hash
    return user


@pytest.fixture
def auth_headers(mock_user):
    """Generate auth headers for authenticated requests."""
    token = create_access_token(str(mock_user.id))
    return {"Authorization": f"Bearer {token}"}
