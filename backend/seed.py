"""
Seed script — creates the initial admin user and optionally a demo PM user.

Usage:
    python seed.py
    python seed.py --email admin@example.com --password secret --name "Admin"
    python seed.py --demo   # also creates a demo PM user
"""
import argparse
import asyncio
import sys
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.database import AsyncSessionLocal
from core.models import User, Role, UserRole, Permission, RolePermission
from core.auth.password import hash_password


async def create_user(
    db,
    email: str,
    password: str,
    display_name: str,
    role_name: str,
) -> User:
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  [skip]  User {email} already exists.")
        return existing

    # Get role
    role_result = await db.execute(select(Role).where(Role.name == role_name))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise RuntimeError(
            f"Role '{role_name}' not found. Run 'alembic upgrade head' first."
        )

    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        preferred_lang="en",
        auth_provider="local",
        is_active=True,
    )
    db.add(user)
    await db.flush()

    db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit()
    print(f"  [ok]  Created {role_name}: {email} / {password}")
    return user


async def main(args) -> None:
    async with AsyncSessionLocal() as db:
        print("\n=== Coffee Time Saver — Database Seed ===\n")

        # Verify roles exist (migration must have run)
        result = await db.execute(select(Role))
        roles = result.scalars().all()
        if not roles:
            print("ERROR: No roles found. Please run migrations first:")
            print("  alembic upgrade head")
            sys.exit(1)
        print(f"Roles found: {[r.name for r in roles]}")

        # Create admin user
        await create_user(
            db,
            email=args.email,
            password=args.password,
            display_name=args.name,
            role_name="admin",
        )

        # Optionally create demo PM user
        if args.demo:
            await create_user(
                db,
                email="pm@example.com",
                password="pm123456",
                display_name="Demo PM",
                role_name="pm",
            )

        print("\nDone! You can now log in at POST /api/auth/login\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Coffee Time Saver database")
    parser.add_argument("--email",    default="admin@example.com", help="Admin email")
    parser.add_argument("--password", default="admin123456",        help="Admin password")
    parser.add_argument("--name",     default="Administrator",      help="Admin display name")
    parser.add_argument("--demo",     action="store_true",          help="Also create a demo PM user")
    args = parser.parse_args()
    asyncio.run(main(args))
