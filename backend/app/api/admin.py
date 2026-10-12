"""Admin / dashboard API stubs used for RBAC enforcement."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_support_or_admin
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import AdminUserResponse, UserResponse

router = APIRouter(prefix="/api", tags=["admin"])


@router.get("/admin/ping", response_model=dict)
def admin_ping(current_user: User = Depends(require_admin)) -> dict:
    """Admin-only health check used to verify RBAC."""
    return {
        "status": "ok",
        "role": current_user.role.value,
        "user": UserResponse.model_validate(current_user).model_dump(mode="json"),
    }


@router.get("/admin/users", response_model=list[AdminUserResponse])
def list_users(
    role: UserRole | None = Query(
        default=None,
        description="Optional role filter, e.g. customer",
    ),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[AdminUserResponse]:
    """List registered users for the admin dashboard (newest first)."""
    stmt = select(User).order_by(User.created_at.desc())
    if role is not None:
        stmt = stmt.where(User.role == role)
    users = db.scalars(stmt).all()
    return [AdminUserResponse.model_validate(user) for user in users]


@router.get("/dashboard/ping", response_model=dict)
def dashboard_ping(current_user: User = Depends(require_support_or_admin)) -> dict:
    """Support/admin health check for dashboard API access."""
    return {
        "status": "ok",
        "role": current_user.role.value,
        "user": UserResponse.model_validate(current_user).model_dump(mode="json"),
    }
