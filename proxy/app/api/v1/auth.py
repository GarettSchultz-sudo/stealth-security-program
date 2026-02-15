"""Authentication API endpoints."""

import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import get_db
from app.models.user import ApiKey, User

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)
settings = get_settings()


class UserRegister(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str
    org_name: str | None = None


class UserLogin(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User response."""

    id: str
    email: str
    org_name: str | None
    plan: str
    is_active: bool


class ApiKeyCreate(BaseModel):
    """API key creation request."""

    name: str


class ApiKeyResponse(BaseModel):
    """API key response."""

    id: str
    name: str
    key_prefix: str
    is_active: bool
    last_used: str | None
    created_at: str


def create_access_token(user_id: str) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": user_id, "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """Create JWT refresh token."""
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key. Returns (full_key, key_hash, key_prefix)."""
    import secrets

    # Generate random key with prefix
    key = f"acc_{secrets.token_hex(24)}"
    key_hash = pwd_context.hash(key)
    key_prefix = key[:12]  # acc_xxxxxxxx

    return key, key_hash, key_prefix


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security)],
) -> uuid.UUID:
    """
    Extract and validate user ID from JWT token.

    This is the proper auth implementation replacing the hardcoded user_id.

    Raises:
        HTTPException: If token is missing, invalid, or user not found

    Returns:
        UUID of the authenticated user
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if user_id is None or token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return uuid.UUID(user_id)

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid user ID in token: {e}")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from JWT token.

    Returns:
        User model instance

    Raises:
        HTTPException: If not authenticated or user not found
    """
    user_id = await get_current_user_id(credentials)
    user = await db.get(User, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    return user


# Type alias for dependency injection
CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user."""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = User(
        email=user_data.email,
        hashed_password=pwd_context.hash(user_data.password),
        org_name=user_data.org_name,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=str(user.id),
        email=user.email,
        org_name=user.org_name,
        plan=user.plan.value,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Login and get tokens."""
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token."""
    try:
        payload = jwt.decode(
            refresh_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = payload.get("sub")
        user = await db.get(User, uuid.UUID(user_id))

        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
            expires_in=settings.access_token_expire_minutes * 60,
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/api-keys", response_model=dict)
async def create_api_key(
    key_data: ApiKeyCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new API key for the proxy."""
    full_key, key_hash, key_prefix = generate_api_key()

    api_key = ApiKey(
        user_id=user.id,
        name=key_data.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
    )

    db.add(api_key)
    await db.commit()

    # Return full key only once
    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key": full_key,  # Only shown once!
        "key_prefix": key_prefix,
        "created_at": api_key.created_at.isoformat(),
        "warning": "Store this key securely. It will not be shown again.",
    }


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyResponse]:
    """List all API keys for the current user."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user.id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()

    return [
        ApiKeyResponse(
            id=str(k.id),
            name=k.name,
            key_prefix=k.key_prefix,
            is_active=k.is_active,
            last_used=k.last_used.isoformat() if k.last_used else None,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke an API key."""
    key = await db.get(ApiKey, uuid.UUID(key_id))

    if not key or key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = False
    await db.commit()

    return {"status": "revoked", "id": key_id}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: CurrentUser,
) -> UserResponse:
    """Get current user info."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        org_name=user.org_name,
        plan=user.plan.value,
        is_active=user.is_active,
    )
