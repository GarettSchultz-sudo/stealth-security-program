"""Seed script to populate pricing data and create test user."""

import asyncio
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# This would be run as: uv run python scripts/seed_pricing.py


async def seed_database():
    """Seed the database with initial data."""
    from passlib.context import CryptContext

    from app.config import get_settings
    from app.models.database import AsyncSessionLocal, init_db
    from app.models.user import ApiKey, User

    settings = get_settings()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    await init_db()

    async with AsyncSessionLocal() as db:
        # Check if test user exists
        result = await db.execute(select(User).where(User.email == "demo@clawshell.io"))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("Test user already exists")
            return

        # Create test user
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="demo@clawshell.io",
            hashed_password=pwd_context.hash("demo123"),
            org_name="Demo Organization",
            is_verified=True,
        )
        db.add(user)

        # Create API key for test user
        api_key = ApiKey(
            user_id=user.id,
            name="Demo API Key",
            key_hash=pwd_context.hash("acc_demo_key_for_testing"),
            key_prefix="acc_demo",
        )
        db.add(api_key)

        await db.commit()
        print("Created test user: demo@clawshell.io")
        print("Password: demo123")
        print("API Key: acc_demo_key_for_testing")


if __name__ == "__main__":
    asyncio.run(seed_database())
