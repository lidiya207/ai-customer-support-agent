"""Interactive CLI to create the first admin user safely."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

# Allow running as `uv run python scripts/create_admin.py` from backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.user import User, UserRole


def prompt_non_empty(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print(f"{label} is required.")


def prompt_password() -> str:
    while True:
        password = getpass.getpass("Password (min 8 characters): ")
        confirm = getpass.getpass("Confirm password: ")
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            continue
        if password != confirm:
            print("Passwords do not match.")
            continue
        return password


def main() -> None:
    print("Create admin user")
    print("-" * 40)
    name = prompt_non_empty("Name")
    email = prompt_non_empty("Email").lower()
    password = prompt_password()

    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            print(f"Error: An account with email '{email}' already exists.")
            sys.exit(1)

        admin = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Admin created successfully: {admin.email} (id={admin.id})")
    except Exception as exc:
        db.rollback()
        print(f"Failed to create admin: {exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
