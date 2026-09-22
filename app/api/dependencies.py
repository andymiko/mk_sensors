from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dbapi.base import get_async_session
from app.dbapi.models.roles import Role
from app.dbapi.models.users import User
from app.utils.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Требуется действительный токен доступа",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise unauthorized from None

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise unauthorized

    user = await db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    if user is None or not user.is_active:
        raise unauthorized

    return user


def require_permission(permission_code: str) -> Callable:
    async def permission_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not current_user.is_admin() and not current_user.has_permission(permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Недостаточно прав: требуется {permission_code}",
            )
        return current_user

    return permission_dependency


CurrentUser = Annotated[User, Depends(get_current_user)]
