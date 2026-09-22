import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import require_permission
from app.dbapi.base import get_async_session
from app.dbapi.models.associations import role_permissions, user_roles
from app.dbapi.models.auths import Auth
from app.dbapi.models.files import Files
from app.dbapi.models.permissions import Permission
from app.dbapi.models.roles import Role
from app.dbapi.models.users import User
from app.schemas.admin import (
    PermissionCreate, PermissionUpdate, RoleCreate, RolePermissionsUpdate,
    RoleUpdate, UserRolesUpdate, UserStatusUpdate,
)
from app.schemas.files import FileModel, FilePage
from app.schemas.users import PermissionModel, RoleModel, UserRead


router = APIRouter(prefix="/admin", tags=["admin"])
Db = Annotated[AsyncSession, Depends(get_async_session)]


@router.get("/users", response_model=list[UserRead])
async def list_users(
    db: Db,
    _current_user: Annotated[User, Depends(require_permission("user.view"))],
):
    users = (
        await db.scalars(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .order_by(User.created_at.desc())
        )
    ).all()
    return [UserRead.model_validate(user) for user in users]


@router.patch("/users/{user_id}/status", response_model=UserRead)
async def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    db: Db,
    current_user: Annotated[User, Depends(require_permission("user.edit"))],
):
    if user_id == current_user.id and not payload.is_active:
        raise HTTPException(400, "Нельзя заблокировать собственный аккаунт")
    user = await db.get(User, user_id)
    credential = await db.get(Auth, user_id)
    if user is None or credential is None:
        raise HTTPException(404, "Пользователь не найден")
    user.is_active = payload.is_active
    credential.is_active = payload.is_active
    await db.commit()
    return await _load_user(db, user_id)


@router.put("/users/{user_id}/roles", response_model=UserRead)
async def replace_user_roles(
    user_id: str,
    payload: UserRolesUpdate,
    db: Db,
    _current_user: Annotated[User, Depends(require_permission("user.edit"))],
):
    if await db.get(User, user_id) is None:
        raise HTTPException(404, "Пользователь не найден")
    role_ids = set(payload.role_ids)
    if role_ids:
        existing = set((await db.scalars(select(Role.id).where(Role.id.in_(role_ids)))).all())
        if existing != role_ids:
            raise HTTPException(400, "Передана неизвестная роль")
    await db.execute(delete(user_roles).where(user_roles.c.user_id == user_id))
    if role_ids:
        await db.execute(user_roles.insert(), [{"user_id": user_id, "role_id": role_id} for role_id in role_ids])
    await db.commit()
    return await _load_user(db, user_id)


@router.get("/roles")
async def list_roles(
    db: Db,
    _current_user: Annotated[User, Depends(require_permission("role.view"))],
):
    roles = (await db.scalars(select(Role).options(selectinload(Role.permissions)).order_by(Role.code))).all()
    return [
        {**RoleModel.model_validate(role).model_dump(), "permissions": [PermissionModel.model_validate(p) for p in role.permissions]}
        for role in roles
    ]


@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(payload: RoleCreate, db: Db, _user: Annotated[User, Depends(require_permission("role.create"))]):
    role = Role(id=str(uuid.uuid4()), **payload.model_dump())
    db.add(role)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Роль с таким кодом уже существует") from None
    return RoleModel.model_validate(role)


@router.patch("/roles/{role_id}", response_model=RoleModel)
async def update_role(role_id: str, payload: RoleUpdate, db: Db, _user: Annotated[User, Depends(require_permission("role.edit"))]):
    role = await db.get(Role, role_id)
    if role is None:
        raise HTTPException(404, "Роль не найдена")
    role.name, role.description = payload.name, payload.description
    await db.commit()
    return RoleModel.model_validate(role)


@router.put("/roles/{role_id}/permissions")
async def replace_role_permissions(role_id: str, payload: RolePermissionsUpdate, db: Db, _user: Annotated[User, Depends(require_permission("role.edit"))]):
    if await db.get(Role, role_id) is None:
        raise HTTPException(404, "Роль не найдена")
    permission_ids = set(payload.permission_ids)
    if permission_ids:
        existing = set((await db.scalars(select(Permission.id).where(Permission.id.in_(permission_ids)))).all())
        if existing != permission_ids:
            raise HTTPException(400, "Передано неизвестное разрешение")
    await db.execute(delete(role_permissions).where(role_permissions.c.role_id == role_id))
    if permission_ids:
        await db.execute(role_permissions.insert(), [{"role_id": role_id, "permission_id": pid} for pid in permission_ids])
    await db.commit()
    return {"role_id": role_id, "permission_ids": sorted(permission_ids)}


@router.get("/permissions", response_model=list[PermissionModel])
async def list_permissions(db: Db, _user: Annotated[User, Depends(require_permission("permission.view"))]):
    return (await db.scalars(select(Permission).order_by(Permission.code))).all()


@router.post("/permissions", response_model=PermissionModel, status_code=status.HTTP_201_CREATED)
async def create_permission(payload: PermissionCreate, db: Db, _user: Annotated[User, Depends(require_permission("permission.create"))]):
    permission = Permission(id=str(uuid.uuid4()), **payload.model_dump())
    db.add(permission)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Разрешение с таким кодом уже существует") from None
    return PermissionModel.model_validate(permission)


@router.patch("/permissions/{permission_id}", response_model=PermissionModel)
async def update_permission(permission_id: str, payload: PermissionUpdate, db: Db, _user: Annotated[User, Depends(require_permission("permission.edit"))]):
    permission = await db.get(Permission, permission_id)
    if permission is None:
        raise HTTPException(404, "Разрешение не найдено")
    permission.name, permission.description = payload.name, payload.description
    await db.commit()
    return PermissionModel.model_validate(permission)


@router.get("/files", response_model=FilePage)
async def list_all_files(
    db: Db,
    current_user: Annotated[User, Depends(require_permission("file.download"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=255),
):
    if not current_user.is_admin():
        raise HTTPException(403, "Доступно только администраторам")
    items, total = await Files.page(
        page=page, page_size=page_size, search=search, db=db,
    )
    return FilePage(items=items, total=total, page=page, page_size=page_size)


async def _load_user(db: AsyncSession, user_id: str) -> UserRead:
    user = await db.scalar(
        select(User).where(User.id == user_id).options(selectinload(User.roles).selectinload(Role.permissions))
    )
    return UserRead.model_validate(user)
