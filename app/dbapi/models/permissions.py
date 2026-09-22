import uuid
from typing import List

from sqlalchemy import String, select
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy.ext.asyncio import AsyncSession

from app.dbapi.base import Base, get_async_db_context

from app.schemas.users import PermissionModel


class Permission(Base):

    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(500))

    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        lazy="selectin")

class PermissionsTable:


    async def insert_new_permission(
        self,
        id: str,
        code: str,
        name: str,
        description: str | None = None,
        db: AsyncSession | None = None,
    ) -> PermissionModel | None:

        async with get_async_db_context(db) as session:
            permission = PermissionModel(
                **{
                    "id": id,
                    "code": code,
                    "name": name,
                    "description": description
                }
            )

            result = Permission(**permission.model_dump())
            session.add(result)
            await session.commit()

            return permission if result else None


    async def get_permission_by_code(
        self, 
        code: str, 
        db: AsyncSession | None = None
    ) -> PermissionModel | None:
        async with get_async_db_context(db) as session:
            permission = await session.execute(
                select(Permission).where(Permission.code == code)
            )
            permission_instance = permission.scalar_one_or_none()

            if permission_instance:
                return PermissionModel.model_validate(permission_instance)
            
            return None


    async def update_permission_description_by_id(
        self,
        id: str,
        new_description: str,
        db: AsyncSession | None = None,
    ) -> bool:
        async with get_async_db_context(db) as session:
            permission_row = await session.get(Permission, id)

            if permission_row is None:
                return False

            permission_row.description = new_description
            await session.commit()
            return True


Permissions = PermissionsTable()
