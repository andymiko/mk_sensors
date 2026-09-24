from typing import Annotated, Callable

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dbapi.base import get_async_session
from app.dbapi.models.roles import Role
from app.dbapi.models.users import User
from app.dbapi.models.api_clients import ApiClient
from app.utils.api_keys import hash_api_token
from app.utils.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)
sensor_token_scheme = APIKeyHeader(name="X-Sensor-Token", auto_error=False)


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


async def get_api_client(
    token: Annotated[str | None, Security(sensor_token_scheme)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> ApiClient:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Требуется действительный сервисный токен",
    )
    if token is None or not 32 <= len(token) <= 512:
        raise unauthorized
    client = await db.scalar(
        select(ApiClient).where(
            ApiClient.token_hash == hash_api_token(token),
            ApiClient.is_active.is_(True),
        )
    )
    if client is None:
        raise unauthorized
    user = await db.get(User, client.user_id)
    if user is None or not user.is_active:
        raise unauthorized
    client.last_used_at = int(datetime.now(timezone.utc).timestamp())
    return client


CurrentApiClient = Annotated[ApiClient, Depends(get_api_client)]
