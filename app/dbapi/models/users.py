from typing import List, Set

from sqlalchemy import String, Boolean, select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import mapped_column, relationship, Mapped

from app.dbapi.base import Base, get_async_db_context

from app.schemas.users import UserModel


class User(Base):

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="Пользователь", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin"
    )
    @property
    def role_codes(self) -> Set[str] | None:
        return { role.code for role in self.roles }

    @property
    def permission_codes(self) -> Set[str] | None:
        permissions: Set[str] = set()

        for role in self.roles:
            for permission in role.permissions:
                permissions.add(permission.code)

        return permissions

    @property
    def permissions(self) -> list["Permission"]:
        permissions = {
            permission.code: permission
            for role in self.roles
            for permission in role.permissions
        }
        return [permissions[code] for code in sorted(permissions)]

    def has_permission(self, permission_code: str) -> bool:
        return permission_code in self.permission_codes

    def has_any_permission(self, *permission_codes: str) -> bool:
        return bool(self.permission_codes & set(permission_codes))

    def has_all_permissions(self, *permission_codes: str) -> bool:
        return set(permission_codes).issubset(self.permission_codes)

    def has_role(self, role_code: str) -> bool:
        return role_code in self.role_codes

    def has_any_role(self, *role_codes: str) -> bool:
        return bool(self.role_codes & set(role_codes))

    def is_admin(self) -> bool:
        return self.has_role("admin")


class UsersTable:


    async def insert_new_user(
        self, 
        id: str,
        email: str,
        name: str,
        is_active: bool,
        db: AsyncSession | None = None
    ) -> UserModel | None:

        async with get_async_db_context(db) as session:
            user = User(
                id=id,
                email=email,
                name=name,
                is_active=is_active)

            session.add(user)
            await session.commit()
            await session.refresh(user)

            return UserModel.model_validate(user) if user else None


    async def get_user_by_id(
        self, 
        id: str, 
        db: AsyncSession | None = None
    ) -> UserModel | None:
            async with get_async_db_context(db) as session:
                user = await session.get(User, id)
    
                if user is None:
                    return None
    
                return UserModel.model_validate(user)


    async def get_user_by_email(
        self, 
        email: str, 
        db: AsyncSession | None = None
    ) -> UserModel | None:
        async with get_async_db_context(db) as session:
            email_filter = func.lower(User.email) == email.lower()
            query = select(User).where(email_filter)

            user = await session.execute(query)
            user_instance = user.scalar_one_or_none()   

            if user_instance is None:
                return None

            return UserModel.model_validate(user_instance)


    async def get_num_users(
        self, 
        db: AsyncSession | None = None
    ) -> int | None:
        async with get_async_db_context(db) as session:
            result = await session.execute(select(func.count()).select_from(User))
            return result.scalar()

    
    async def update_user_by_id(
        self, 
        id: str, 
        updated: dict, 
        db: AsyncSession | None = None
    ) -> UserModel | None:
        async with get_async_db_context(db) as session:
            user = await session.get(User, id)
            if not user:
                return None

            for key, value in updated.items():
                setattr(user, key, value)

            await session.commit()
            await session.refresh(user)

            return UserModel.model_validate(user) if user else None


    async def delete_user_by_id(
        self,
        id: str,
        db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as session:
            await session.execute(delete(User).where(User.id == id))
            await session.commit()
            return True


Users = UsersTable()
