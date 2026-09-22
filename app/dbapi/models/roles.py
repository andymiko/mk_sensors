import uuid
from typing import List

from sqlalchemy import String, select
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy.ext.asyncio import AsyncSession

from app.dbapi.base import Base, get_async_db_context

from app.schemas.users import RoleModel


class Role(Base):

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    users: Mapped[List["User"]] = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
    )
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )

class RolesTable:


    async def insert_new_role(
        self,
        id: str,
        code: str,
        name: str,
        description: str | None = None,
        db: AsyncSession | None = None,
    ) -> RoleModel | None:

        async with get_async_db_context(db) as session:
            role = RoleModel(
                **{
                    "id": id,
                    "code": code,
                    "name": name,
                    "description": description
                }
            )

            result = Role(**role.model_dump())
            session.add(result)
            await session.commit()

            return role if result else None


    async def get_role_by_code(
        self, code: 
        str, db: 
        AsyncSession | None = None
    ) -> RoleModel | None:
        async with get_async_db_context(db) as session:
            role = await session.execute(
                select(Role).where(Role.code == code)
            )
            role_instance = role.scalar_one_or_none()

            if role_instance:
                return RoleModel.model_validate(role_instance)
            return None


    async def update_role_description_by_id(
        self,
        id: str,
        new_description: str,
        db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as session:
            role_row = await session.get(Role, id)
            if role_row is None:
                return False

            role_row.description = new_description
            await session.commit()
            return True
            


Roles = RolesTable()
