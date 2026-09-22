from sqlalchemy import ForeignKey, Table, Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.dbapi.base import Base, get_async_db_context


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
)

class RolePermissionAssociation:
    async def link_permission_to_role(
            self, 
            role_id: str, 
            permission_id: str, 
            db: AsyncSession | None = None
            ) -> None:
        async with get_async_db_context(db) as session:
            await session.execute(
                role_permissions.insert().values(role_id=role_id, permission_id=permission_id)
            )
            await session.commit()

    async def unlink_permission_from_role(
            self, 
            role_id: str, 
            permission_id: str | None = None, 
            db: AsyncSession | None = None
            ) -> None:
        async with get_async_db_context(db) as session:

            if permission_id is None:
                await session.execute(
                    role_permissions.delete().where(
                        role_permissions.c.role_id == role_id
                        ))

                await session.commit()
                return

            await session.execute(
                role_permissions.delete().where(
                    role_permissions.c.role_id == role_id,
                    role_permissions.c.permission_id == permission_id
                )
            )
            await session.commit()

class UserRoleAssociation:
    async def link_role_to_user(
            self, 
            user_id: str, 
            role_id: str, 
            db: AsyncSession | None = None
            ) -> None:
        async with get_async_db_context(db) as session:
            await session.execute(
                user_roles.insert().values(user_id=user_id, role_id=role_id)
            )
            await session.commit()

    async def unlink_role_from_user(
            self, 
            user_id: str,
            role_id: str | None = None, 
            db: AsyncSession | None = None
            ) -> None:
        async with get_async_db_context(db) as session:

            if role_id is None:
                await session.execute(
                    user_roles.delete().where(
                        user_roles.c.user_id == user_id
                    )
                )
                await session.commit()
                return
            
            await session.execute(
                user_roles.delete().where(
                    user_roles.c.user_id == user_id,
                    user_roles.c.role_id == role_id
                )
            )
            await session.commit()

RolePermissionAssociation = RolePermissionAssociation()
UserRoleAssociation = UserRoleAssociation()